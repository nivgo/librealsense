#include "json_normalizer.h"
#include "json.hpp"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <regex>
#include <iostream>

using json = nlohmann::json;

// Implementation class that contains all the JSON-dependent logic
class UIJsonNormalizerImpl {
public:
    struct ComboInfo {
        size_t combo_idx = 0;
        size_t popup_idx = 0;
        std::vector<size_t> option_indices;
        uint64_t owner_id = 0;
        bool has_popup = false;
    };

    UIJsonNormalizer::NormalizationOptions options_;
    std::set<uint64_t> container_ids_;
    std::map<uint64_t, size_t> node_index_map_;
    std::map<uint64_t, size_t> id_to_index_;

    explicit UIJsonNormalizerImpl(const UIJsonNormalizer::NormalizationOptions& opts) : options_(opts) {}

    void normalize_json_object(json& json_obj) {
        // Clear previous state
        container_ids_.clear();
        node_index_map_.clear();
        id_to_index_.clear();

        // 8-stage normalization pipeline
        if (options_.preserve_original_ids) stage_1_parse_and_index(json_obj);
        stage_2_normalize_basic_fields(json_obj);
        if (options_.fix_container_hierarchy) stage_3_fix_types_and_controls(json_obj);
        if (options_.auto_detect_combos) stage_4_fix_combos_and_popups(json_obj);
        stage_5_reparent_options(json_obj);
        if (options_.deduplicate_nodes) stage_6_deduplicate_nodes(json_obj);
        if (options_.assign_z_indices) stage_7_assign_z_order(json_obj);
        if (options_.validate_output) stage_8_validate_result(json_obj);
    }

    void stage_1_parse_and_index(json& json_obj) {
        // Ensure ui_version is 1.2.0
        json_obj["ui_version"] = "1.2.0";
        
        // Index all nodes and containers
        if (json_obj.contains("nodes") && json_obj["nodes"].is_array()) {
            auto& nodes = json_obj["nodes"];
            for (size_t i = 0; i < nodes.size(); ++i) {
                auto& node = nodes[i];
                if (node.contains("id")) {
                    uint64_t id = node["id"];
                    id_to_index_[id] = i;
                    
                    // Check if this is a container
                    if (node.contains("type")) {
                        std::string type = node["type"];
                        if (is_container_type(type)) {
                            container_ids_.insert(id);
                        }
                    }
                }
            }
        }
        
        // Index containers from the containers object
        if (json_obj.contains("containers") && json_obj["containers"].is_object()) {
            for (auto& item : json_obj["containers"].items()) {
                try {
                    uint64_t container_id = std::stoull(item.key());
                    container_ids_.insert(container_id);
                } catch (...) {
                    // Skip invalid container IDs
                }
            }
        }
    }

    void stage_2_normalize_basic_fields(json& json_obj) {
        if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) {
            return;
        }

        auto& nodes = json_obj["nodes"];
        for (auto& node : nodes) {
            // Ensure all v1.2.0 fields exist with defaults
            if (!node.contains("label")) node["label"] = "";
            if (!node.contains("type")) node["type"] = "control";
            if (!node.contains("visible")) node["visible"] = true;
            if (!node.contains("enabled")) node["enabled"] = true;
            if (!node.contains("disabled")) node["disabled"] = false;
            
            // v1.2.0 new fields
            if (!node.contains("aliases")) node["aliases"] = json::array();
            if (!node.contains("drag_axis")) node["drag_axis"] = "none";
            if (!node.contains("z_index")) node["z_index"] = 0;
            
            // Normalize label to human-readable form
            if (options_.normalize_labels && node.contains("label")) {
                std::string raw_label = node["label"];
                node["label"] = normalize_label(raw_label);
            }
        }
    }

    void stage_3_fix_types_and_controls(json& json_obj) {
        if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) {
            return;
        }

        auto& nodes = json_obj["nodes"];
        for (auto& node : nodes) {
            // Auto-detect control type if not properly set
            std::string current_type = node.value("type", "");
            if (current_type.empty() || current_type == "control" || current_type == "unknown") {
                std::string detected_type = detect_control_type(node);
                if (!detected_type.empty() && detected_type != "control") {
                    node["type"] = detected_type;
                }
            }
            
            // Add type-specific metadata
            std::string type = node.value("type", "");
            if (type == "slider") {
                if (!node.contains("min")) node["min"] = 0.0;
                if (!node.contains("max")) node["max"] = 100.0;
                if (!node.contains("value")) node["value"] = 0.0;
                if (!node.contains("step")) node["step"] = 1.0;
                node["drag_axis"] = "horizontal"; // Default for sliders
            } else if (type == "button") {
                if (!node.contains("pressed")) node["pressed"] = false;
            } else if (type == "checkbox") {
                if (!node.contains("checked")) node["checked"] = false;
            } else if (type == "combo") {
                if (!node.contains("selected_index")) node["selected_index"] = 0;
                if (!node.contains("options")) node["options"] = json::array();
            }
        }
    }

    void stage_4_fix_combos_and_popups(json& json_obj) {
        if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) {
            return;
        }

        auto combo_groups = detect_combo_popup_groups(json_obj["nodes"]);
        for (const auto& combo_info : combo_groups) {
            normalize_combo_group(json_obj["nodes"], combo_info);
        }
    }

    void stage_5_reparent_options(json& json_obj) {
        if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) {
            return;
        }

        auto& nodes = json_obj["nodes"];
        std::vector<size_t> orphan_indices;
        std::map<uint64_t, size_t> popup_indices;

        // Find popups and orphaned options
        for (size_t i = 0; i < nodes.size(); ++i) {
            auto& node = nodes[i];
            std::string type = node.value("type", "");
            
            if (type == "popup" || type == "popup_window") {
                uint64_t popup_id = node.value("id", 0ULL);
                popup_indices[popup_id] = i;
            } else if (type == "option" || type == "combo_option") {
                // Check if this option has a proper parent
                uint64_t parent_id = node.value("parent_id", 0ULL);
                if (parent_id == 0 || id_to_index_.find(parent_id) == id_to_index_.end()) {
                    orphan_indices.push_back(i);
                }
            }
        }

        // Reparent orphaned options to appropriate popups
        for (size_t orphan_idx : orphan_indices) {
            auto& orphan = nodes[orphan_idx];
            uint64_t owner_id = orphan.value("owner_id", 0ULL);
            
            if (owner_id == 0) continue;
            
            // Find the popup that belongs to this owner
            for (auto& popup_item : popup_indices) {
                auto& popup = nodes[popup_item.second];
                if (popup.value("owner_id", 0ULL) == owner_id) {
                    // Move orphan to popup's nodes array
                    if (!popup.contains("nodes")) {
                        popup["nodes"] = json::array();
                    }
                    popup["nodes"].push_back(orphan);
                    
                    // Mark for removal from main nodes array
                    orphan["_to_remove"] = true;
                    break;
                }
            }
        }

        // Remove orphaned nodes that were reparented
        nodes.erase(
            std::remove_if(nodes.begin(), nodes.end(),
                [](const json& node) { return node.value("_to_remove", false); }),
            nodes.end()
        );
    }

    void stage_6_deduplicate_nodes(json& json_obj) {
        if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) {
            return;
        }

        auto& nodes = json_obj["nodes"];
        std::map<std::string, std::vector<size_t>> label_groups;

        // Group nodes by normalized label
        for (size_t i = 0; i < nodes.size(); ++i) {
            auto& node = nodes[i];
            std::string label = normalize_label(node.value("label", ""));
            if (!label.empty()) {
                label_groups[label].push_back(i);
            }
        }

        // For each group with duplicates, keep the most complete one
        for (const auto& group : label_groups) {
            if (group.second.size() <= 1) continue;

            size_t best_idx = group.second[0];
            int best_score = 0;

            // Score nodes based on completeness
            for (size_t idx : group.second) {
                auto& node = nodes[idx];
                int score = 0;
                
                // Higher score for nodes with more fields
                score += node.size();
                if (node.contains("type") && node["type"] != "control") score += 5;
                if (node.contains("value")) score += 3;
                if (node.contains("options") && node["options"].is_array()) score += 10;
                
                if (score > best_score) {
                    best_score = score;
                    best_idx = idx;
                }
            }

            // Mark others for removal
            for (size_t idx : group.second) {
                if (idx != best_idx) {
                    nodes[idx]["_to_remove"] = true;
                }
            }
        }

        // Remove marked duplicates
        nodes.erase(
            std::remove_if(nodes.begin(), nodes.end(),
                [](const json& node) { return node.value("_to_remove", false); }),
            nodes.end()
        );
    }

    void stage_7_assign_z_order(json& json_obj) {
        if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) {
            return;
        }

        assign_z_indices_by_category(json_obj["nodes"]);
    }

    void stage_8_validate_result(json& json_obj) {
        // Basic validation of the normalized result
        if (!validate_normalized_json(json_obj)) {
            throw std::runtime_error("Normalized JSON failed validation");
        }
    }

    std::string normalize_label(const std::string& raw_label) {
        if (raw_label.empty()) return "";

        // Remove common UI prefixes/suffixes
        std::string result = raw_label;
        
        // Remove patterns like "##", "###", etc. (ImGui ID markers)
        result = std::regex_replace(result, std::regex("#+$"), "");
        
        // Remove patterns like "_ctrl", "_button", etc.
        result = std::regex_replace(result, std::regex("_(ctrl|button|slider|combo|text)$"), "");
        
        // Convert underscores to spaces
        result = std::regex_replace(result, std::regex("_"), " ");
        
        // Capitalize first letter of each word
        bool capitalize_next = true;
        for (char& c : result) {
            if (std::isspace(c)) {
                capitalize_next = true;
            } else if (capitalize_next) {
                c = std::toupper(c);
                capitalize_next = false;
            }
        }
        
        return result;
    }

    std::string detect_control_type(const json& node) {
        std::string label = node.value("label", "");
        std::string clean_label = normalize_label(label);
        
        // Basic type mapping from UI patterns
        static const std::map<std::string, std::string> known_mappings = {
            {"button", "button"}, {"checkbox", "checkbox"}, {"slider", "slider"},
            {"combo", "combo"}, {"text", "text"}, {"image", "image"},
            {"group", "group"}, {"tab", "tab"}, {"window", "window"},
            {"popup", "popup"}, {"radio", "radio"}, {"progress", "progress"},
            {"separator", "separator"}, {"spacer", "spacer"}, {"tooltip", "tooltip"}
        };
        
        std::string lower_result = clean_label;
        std::transform(lower_result.begin(), lower_result.end(), lower_result.begin(), ::tolower);
        
        for (const auto& mapping : known_mappings) {
            if (lower_result.find(mapping.first) != std::string::npos) {
                return mapping.second;
            }
        }
        
        // Check for combo-like controls based on typical patterns
        if (is_combo_like(node)) return "combo";
        if (is_button_like(node)) return "button";
        if (is_header_like(node)) return "group";
        
        return "control";
    }

    bool is_container_type(const std::string& type) {
        static const std::set<std::string> container_types = {
            "window", "group", "tab", "popup", "panel", "frame", "container"
        };
        return container_types.find(type) != container_types.end();
    }

    bool is_combo_like(const json& node) {
        std::string label = node.value("label", "");
        
        // Regex patterns for combo-like controls
        static const std::vector<std::regex> combo_patterns = {
            std::regex(".*combo.*", std::regex_constants::icase),
            std::regex(".*dropdown.*", std::regex_constants::icase),
            std::regex(".*select.*", std::regex_constants::icase)
        };
        
        for (const auto& pattern : combo_patterns) {
            if (std::regex_match(label, pattern)) {
                return true;
            }
        }
        
        return false;
    }

    bool is_button_like(const json& node) {
        std::string label = node.value("label", "");
        
        static const std::vector<std::regex> button_patterns = {
            std::regex(".*button.*", std::regex_constants::icase),
            std::regex(".*btn.*", std::regex_constants::icase),
            std::regex(".*click.*", std::regex_constants::icase),
            std::regex(".*press.*", std::regex_constants::icase)
        };
        
        for (const auto& pattern : button_patterns) {
            if (std::regex_match(label, pattern)) {
                return true;
            }
        }
        
        return false;
    }

    bool is_header_like(const json& node) {
        std::string label = node.value("label", "");
        
        static const std::vector<std::regex> header_patterns = {
            std::regex(".*header.*", std::regex_constants::icase),
            std::regex(".*group.*", std::regex_constants::icase),
            std::regex(".*section.*", std::regex_constants::icase)
        };
        
        for (const auto& pattern : header_patterns) {
            if (std::regex_match(label, pattern)) {
                return true;
            }
        }
        
        return false;
    }

    void calculate_visibility_state(json& node, const json& display, const json& containers) {
        // Basic visibility calculation - this can be enhanced
        bool visible = true;
        
        // Check if node is in display list
        if (display.is_object() && display.contains("visible_nodes")) {
            uint64_t node_id = node.value("id", 0ULL);
            bool found_in_display = false;
            
            for (const auto& visible_id : display["visible_nodes"]) {
                if (visible_id == node_id) {
                    found_in_display = true;
                    break;
                }
            }
            
            visible = found_in_display;
        }
        
        // Check container visibility
        uint64_t container_id = node.value("container_id", 0ULL);
        if (container_id != 0 && containers.is_object()) {
            std::string container_key = std::to_string(container_id);
            if (containers.contains(container_key)) {
                auto& container = containers[container_key];
                if (container.contains("visible") && !container["visible"]) {
                    visible = false;
                }
            }
        }
        
        node["visible"] = visible;
    }

    std::vector<ComboInfo> detect_combo_popup_groups(const json& nodes) {
        std::vector<ComboInfo> combo_groups;
        
        // Simple combo detection - look for combo + popup pairs
        for (size_t i = 0; i < nodes.size(); ++i) {
            const auto& node = nodes[i];
            std::string type = node.value("type", "");
            
            if (type == "combo" || is_combo_like(node)) {
                ComboInfo info;
                info.combo_idx = i;
                info.owner_id = node.value("id", 0ULL);
                
                // Look for associated popup
                for (size_t j = 0; j < nodes.size(); ++j) {
                    if (i == j) continue;
                    
                    const auto& other = nodes[j];
                    std::string other_type = other.value("type", "");
                    
                    if ((other_type == "popup" || other_type == "popup_window") &&
                        other.value("owner_id", 0ULL) == info.owner_id) {
                        info.popup_idx = j;
                        info.has_popup = true;
                        break;
                    }
                }
                
                combo_groups.push_back(info);
            }
        }
        
        return combo_groups;
    }

    void normalize_combo_group(json& nodes, const ComboInfo& combo_info) {
        auto& combo = nodes[combo_info.combo_idx];
        
        // Ensure combo has proper structure
        if (!combo.contains("options")) {
            combo["options"] = json::array();
        }
        
        if (combo_info.has_popup && combo_info.popup_idx < nodes.size()) {
            auto& popup = nodes[combo_info.popup_idx];
            
            // Move options from popup to combo
            if (popup.contains("nodes") && popup["nodes"].is_array()) {
                for (const auto& option : popup["nodes"]) {
                    if (option.value("type", "") == "option" || 
                        option.value("type", "") == "combo_option") {
                        combo["options"].push_back(option.value("label", ""));
                    }
                }
            }
            
            // Mark popup for removal or hide it
            popup["visible"] = false;
            popup["_combo_processed"] = true;
        }
    }

    void fix_container_references(json& nodes) {
        // Fix any broken container references
        for (auto& node : nodes) {
            uint64_t container_id = node.value("container_id", 0ULL);
            if (container_id != 0) {
                // Verify container exists
                if (container_ids_.find(container_id) == container_ids_.end()) {
                    // Try to find nearest valid container
                    uint64_t node_id = node.value("id", 0ULL);
                    uint64_t nearest = find_nearest_container(node_id, nodes);
                    if (nearest != 0) {
                        node["container_id"] = nearest;
                    } else {
                        node.erase("container_id"); // Remove invalid reference
                    }
                }
            }
        }
    }

    uint64_t find_nearest_container(uint64_t node_id, const json& nodes) {
        // Simple implementation - find first available container
        for (uint64_t container_id : container_ids_) {
            return container_id; // Return first valid container for now
        }
        return 0;
    }

    void assign_z_indices_by_category(json& nodes) {
        // Assign z-indices based on control type categories
        static const std::map<std::string, int> type_z_order = {
            {"window", 1000}, {"popup", 900}, {"tooltip", 800},
            {"group", 100}, {"tab", 90}, {"button", 50},
            {"combo", 40}, {"slider", 30}, {"checkbox", 20},
            {"text", 10}, {"image", 5}, {"separator", 1}
        };

        for (auto& node : nodes) {
            std::string type = node.value("type", "control");
            int base_z = type_z_order.count(type) ? type_z_order.at(type) : 25;
            
            // Add small random offset to avoid exact duplicates
            node["z_index"] = base_z + (node.value("id", 0ULL) % 10);
        }
    }

    bool validate_normalized_json(const json& json_obj) {
        // Basic validation checks
        if (!json_obj.contains("ui_version")) return false;
        if (json_obj["ui_version"] != "1.2.0") return false;
        
        if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) return false;
        
        // Validate each node has required fields
        for (const auto& node : json_obj["nodes"]) {
            if (!node.contains("label") || !node.contains("type")) return false;
            if (!node.contains("visible") || !node.contains("enabled")) return false;
        }
        
        return true;
    }
};

// UIJsonNormalizer public interface implementation
UIJsonNormalizer::UIJsonNormalizer(const NormalizationOptions& opts) 
    : impl_(new UIJsonNormalizerImpl(opts)) {
}

UIJsonNormalizer::UIJsonNormalizer() 
    : impl_(new UIJsonNormalizerImpl(NormalizationOptions())) {
}

UIJsonNormalizer::~UIJsonNormalizer() {
    delete impl_;
}

std::string UIJsonNormalizer::normalize_json_string(const std::string& input_json) {
    try {
        json json_obj = json::parse(input_json);
        impl_->normalize_json_object(json_obj);
        return json_obj.dump(4); // Pretty-printed with 4 spaces
    } catch (const std::exception& e) {
        throw std::runtime_error("JSON normalization failed: " + std::string(e.what()));
    }
}

// Standalone utility functions
std::string normalize_ui_json_to_v1_2(const std::string& json_string) {
    UIJsonNormalizer normalizer;
    return normalizer.normalize_json_string(json_string);
}

bool validate_ui_json_v1_2(const std::string& json_string) {
    try {
        json json_obj = json::parse(json_string);
        UIJsonNormalizer::NormalizationOptions opts;
        UIJsonNormalizerImpl impl(opts);
        return impl.validate_normalized_json(json_obj);
    } catch (...) {
        return false;
    }
}
