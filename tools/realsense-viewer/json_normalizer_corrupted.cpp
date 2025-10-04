#include "json_normalizer.h"
#include "json.hpp"
#include <fstream>
#inclstd::string UIJsonNormalizerImpl::normalize_json_string(const std::string& input_json) {
    try {
        json json_obj = json::parse(input_json);
        impl_->normalize_json_object(json_obj);
        return json_obj.dump(4); // Pretty-printed with 4 spaces
    } catch (const std::exception& e) {
        throw std::runtime_error("JSON normalization failed: " + std::string(e.what()));
    }
}eam>
#include <algorithm>
#include <regex>
#include <iostream>

using json = nlohmann::json;

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

    UIJsonNormalizerImpl::NormalizationOptions options_;
    std::set<uint64_t> container_ids_;
    std::map<uint64_t, size_t> node_index_map_;
    std::map<uint64_t, size_t> id_to_index_;

    explicit UIJsonNormalizerImpl(const UIJsonNormalizerImpl::NormalizationOptions& opts) : options_(opts) {}

    // All the implementation methods that were previously in UIJsonNormalizer
    void normalize_json_object(json& json_obj);
    void stage_1_parse_and_index(json& json_obj);
    void stage_2_normalize_basic_fields(json& json_obj);
    void stage_3_fix_types_and_controls(json& json_obj);
    void stage_4_fix_combos_and_popups(json& json_obj);
    void stage_5_reparent_options(json& json_obj);
    void stage_6_deduplicate_nodes(json& json_obj);
    void stage_7_assign_z_order(json& json_obj);
    void stage_8_validate_result(json& json_obj);

    std::string normalize_label(const std::string& raw_label);
    std::string detect_control_type(const json& node);
    bool is_container_type(const std::string& type);
    bool is_combo_like(const json& node);
    bool is_button_like(const json& node);
    bool is_header_like(const json& node);
    void calculate_visibility_state(json& node, const json& display, const json& containers);
    std::vector<ComboInfo> detect_combo_popup_groups(const json& nodes);
    void normalize_combo_group(json& nodes, const ComboInfo& combo_info);
    void fix_container_references(json& nodes);
    uint64_t find_nearest_container(uint64_t node_id, const json& nodes);
    void assign_z_indices_by_category(json& nodes);
    bool validate_normalized_json(const json& json_obj);
};

// UIJsonNormalizer public interface implementation
UIJsonNormalizerImpl::UIJsonNormalizer(const NormalizationOptions& opts) 
    : impl_(new UIJsonNormalizerImpl(opts)) {
}

UIJsonNormalizerImpl::~UIJsonNormalizer() {
    delete impl_;
}

std::string UIJsonNormalizerImpl::normalize_json_string(const std::string& input_json) {
    try {
        json json_obj = json::parse(input_json);
        normalize_json_object(json_obj);
        return json_obj.dump(2); // Pretty print with 2-space indent
    } catch (const std::exception& e) {
        throw std::runtime_error("JSON normalization failed: " + std::string(e.what()));
    }
}

void UIJsonNormalizerImpl::normalize_json_object(json& json_obj) {
    validation_errors_.clear();
    id_to_index_.clear();
    container_ids_.clear();
    parent_to_children_.clear();
    
    // Run normalization pipeline
    stage_1_parse_and_index(json_obj);
    stage_2_normalize_basic_fields(json_obj);
    stage_3_fix_types_and_controls(json_obj);
    stage_4_fix_combos_and_popups(json_obj);
    stage_5_reparent_options(json_obj);
    stage_6_deduplicate_nodes(json_obj);
    stage_7_assign_z_order(json_obj);
    
    if (options_.validate_output) {
        stage_8_validate_result(json_obj);
    }
}

void UIJsonNormalizerImpl::stage_1_parse_and_index(json& json_obj) {
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

void UIJsonNormalizerImpl::stage_2_normalize_basic_fields(json& json_obj) {
    if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) {
        return;
    }
    
    auto& nodes = json_obj["nodes"];
    auto display = json_obj.value("display", json::array({1920, 1080}));
    auto containers = json_obj.value("containers", json::object());
    
    for (auto& node : nodes) {
        // Ensure required fields exist
        if (!node.contains("onscreen")) {
            node["onscreen"] = true;
        }
        if (!node.contains("visible_area")) {
            node["visible_area"] = node.value("onscreen", true) ? 1.0 : 0.0;
        }
        if (!node.contains("offscreen_reason")) {
            node["offscreen_reason"] = node.value("onscreen", true) ? "" : "unknown";
        }
        if (!node.contains("z_index")) {
            node["z_index"] = 0;
        }
        if (!node.contains("container_id")) {
            node["container_id"] = 0;
        }
        
        // Calculate proper visibility state
        calculate_visibility_state(node, display, containers);
        
        // Normalize labels
        if (options_.normalize_labels && node.contains("label_raw")) {
            std::string raw_label = node["label_raw"];
            std::string norm_label = normalize_label(raw_label);
            if (!norm_label.empty()) {
                node["label_norm"] = norm_label;
            }
            
            // Extract disabled state from label
            if (raw_label.find("_DISABLED:true") != std::string::npos) {
                node["disabled"] = true;
                node["enabled"] = false;
            } else if (raw_label.find("_DISABLED:false") != std::string::npos) {
                node["disabled"] = false;
                node["enabled"] = true;
            }
        }
    }
    
    // Fix container references
    if (options_.fix_container_hierarchy) {
        fix_container_references(nodes);
    }
}

void UIJsonNormalizerImpl::stage_3_fix_types_and_controls(json& json_obj) {
    if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) {
        return;
    }
    
    auto& nodes = json_obj["nodes"];
    
    for (auto& node : nodes) {
        if (!node.contains("type")) continue;
        
        std::string original_type = node["type"];
        std::string new_type = detect_control_type(node);
        
        if (new_type != original_type) {
            node["type"] = new_type;
        }
        
        // Normalize scrollbar types
        if (original_type == "scrollbarY") {
            node["type"] = "scrollbar";
            node["drag_axis"] = "y";
        } else if (original_type == "scrollbarX") {
            node["type"] = "scrollbar";
            node["drag_axis"] = "x";
        }
        
        // Normalize window types
        if (original_type == "window.auto") {
            node["type"] = "window";
        } else if (original_type == "popup_window") {
            node["type"] = "popup";
        } else if (original_type == "tooltip_window") {
            node["type"] = "tooltip";
        }
        
        // Set appropriate actions based on type
        std::string final_type = node["type"];
        if (!node.contains("actions") || node["actions"].empty()) {
            if (final_type == "button") {
                node["actions"] = json::array({"click"});
            } else if (final_type == "checkbox") {
                node["actions"] = json::array({"click"});
            } else if (final_type == "slider" || final_type == "drag") {
                node["actions"] = json::array({"drag", "click"});
                node["type"] = "slider"; // Normalize drag to slider
            } else if (final_type == "combo") {
                node["actions"] = json::array({"open", "select"});
            } else if (final_type == "selectable") {
                node["actions"] = json::array({"click"});
            } else if (final_type == "header") {
                node["actions"] = json::array({"click"});
            }
        }
    }
}

void UIJsonNormalizerImpl::stage_4_fix_combos_and_popups(json& json_obj) {
    if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) {
        return;
    }
    
    auto& nodes = json_obj["nodes"];
    
    // Detect combo-popup groups
    auto combo_groups = detect_combo_popup_groups(nodes);
    
    // Normalize each combo group
    for (const auto& combo_info : combo_groups) {
        normalize_combo_group(nodes, combo_info);
    }
}

void UIJsonNormalizerImpl::stage_5_reparent_options(json& json_obj) {
    if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) {
        return;
    }
    
    auto& nodes = json_obj["nodes"];
    
    // Move orphaned selectable options to their popup parents
    std::vector<size_t> orphan_indices;
    std::unordered_map<uint64_t, size_t> popup_indices;
    
    // Find popups and orphaned selectables
    for (size_t i = 0; i < nodes.size(); ++i) {
        auto& node = nodes[i];
        if (node.value("type", "") == "popup" && node.contains("id")) {
            popup_indices[node["id"]] = i;
        } else if (node.value("type", "") == "selectable" && 
                   node.contains("owner_id") && 
                   !node.contains("parent_popup_processed")) {
            // This is an orphaned option
            orphan_indices.push_back(i);
        }
    }
    
    // Reparent orphaned options
    for (size_t orphan_idx : orphan_indices) {
        auto& orphan = nodes[orphan_idx];
        if (!orphan.contains("owner_id")) continue;
        
        uint64_t owner_id = orphan["owner_id"];
        
        // Find the popup that belongs to this owner
        for (auto& popup_item : popup_indices) {
            auto& popup = nodes[popup_item.second];
            if (popup.value("owner_id", 0ULL) == owner_id) {
                // Move orphan to popup's nodes array
                if (!popup.contains("nodes")) {
                    popup["nodes"] = json::array();
                }
                popup["nodes"].push_back(orphan);
                orphan["parent_popup_processed"] = true;
                break;
            }
        }
    }
    
    // Remove processed orphaned nodes from main nodes array
    nodes.erase(
        std::remove_if(nodes.begin(), nodes.end(),
            [](const json& node) {
                return node.contains("parent_popup_processed");
            }),
        nodes.end()
    );
}

void UIJsonNormalizerImpl::stage_6_deduplicate_nodes(json& json_obj) {
    if (!options_.deduplicate_nodes || !json_obj.contains("nodes")) {
        return;
    }
    
    auto& nodes = json_obj["nodes"];
    std::unordered_map<uint64_t, size_t> id_to_primary;
    std::vector<size_t> duplicates_to_remove;
    
    for (size_t i = 0; i < nodes.size(); ++i) {
        auto& node = nodes[i];
        if (!node.contains("id")) continue;
        
        uint64_t id = node["id"];
        if (id_to_primary.find(id) != id_to_primary.end()) {
            // This is a duplicate - merge with primary
            size_t primary_idx = id_to_primary[id];
            auto& primary = nodes[primary_idx];
            
            // Add label to aliases if different
            if (node.contains("label_raw") && primary.contains("label_raw")) {
                std::string node_label = node["label_raw"];
                std::string primary_label = primary["label_raw"];
                
                if (node_label != primary_label) {
                    if (!primary.contains("aliases")) {
                        primary["aliases"] = json::array();
                    }
                    primary["aliases"].push_back(node_label);
                }
            }
            
            duplicates_to_remove.push_back(i);
        } else {
            id_to_primary[id] = i;
        }
    }
    
    // Remove duplicates (in reverse order to maintain indices)
    std::sort(duplicates_to_remove.rbegin(), duplicates_to_remove.rend());
    for (size_t idx : duplicates_to_remove) {
        nodes.erase(nodes.begin() + idx);
    }
}

void UIJsonNormalizerImpl::stage_7_assign_z_order(json& json_obj) {
    if (!options_.assign_z_indices || !json_obj.contains("nodes")) {
        return;
    }
    
    auto& nodes = json_obj["nodes"];
    assign_z_indices_by_category(nodes);
}

void UIJsonNormalizerImpl::stage_8_validate_result(json& json_obj) {
    if (!validate_normalized_json(json_obj)) {
        std::string error_msg = "Validation failed:";
        for (const auto& error : validation_errors_) {
            error_msg += "\n  - " + error;
        }
        throw std::runtime_error(error_msg);
    }
}

std::string UIJsonNormalizerImpl::normalize_label(const std::string& raw_label) {
    if (raw_label.empty()) return "";
    
    std::string result = raw_label;
    
    // Remove common icon patterns (UTF-8 icons, glyphs)
    static const std::vector<std::regex> icon_patterns = {
        std::regex(R"([📁📂📄📋🔧⚙️🎛️⏸️⏺️⏹️🔄🔁▶️⏯️💾🗂️])"),  // Common UI icons
        std::regex(R"(\uF[0-9A-F]{3})"),  // FontAwesome private use area
        std::regex(R"(\u[2-3][0-9A-F]{3})"),  // Various symbol blocks
    };
    
    for (const auto& pattern : icon_patterns) {
        result = std::regex_replace(result, pattern, "");
    }
    
    // Remove ID patterns
    static const std::vector<std::regex> id_patterns = {
        std::regex(R"([A-Z_]+_ID:\d+)"),  // BUTTON_ID:123
        std::regex(R"(##[^/]+/)"),        // ##Intel RealSense.../
        std::regex(R"(_DISABLED:(true|false))"),  // _DISABLED:true
        std::regex(R"([A-F0-9]{8,})"),    // Long hex strings
        std::regex(R"(\b\d{4,}\b)"),      // Long number sequences
    };
    
    for (const auto& pattern : id_patterns) {
        result = std::regex_replace(result, pattern, "");
    }
    
    // Extract meaningful text after common separators
    static const std::vector<std::string> separators = {"/", ":", "..."};
    for (const auto& sep : separators) {
        size_t pos = result.rfind(sep);
        if (pos != std::string::npos && pos + sep.length() < result.length()) {
            result = result.substr(pos + sep.length());
            break;
        }
    }
    
    // Clean up whitespace and common noise
    result = std::regex_replace(result, std::regex(R"(\s+)"), " ");
    result = std::regex_replace(result, std::regex(R"(^\s+|\s+$)"), "");
    
    // Handle special cases for known control names
    static const std::unordered_map<std::string, std::string> known_mappings = {
        {"auto_exposure", "Auto Exposure"},
        {"visual_preset", "Visual Preset"},
        {"fps", "FPS"},
        {"resolution", "Resolution"},
        {"format", "Format"},
        {"post_processing", "Post Processing"},
        {"advanced_controls", "Advanced Controls"},
        {"save_config", "Save Configuration"},
        {"load_config", "Load Configuration"},
        {"restore_defaults", "Restore Defaults"},
    };
    
    std::string lower_result = result;
    std::transform(lower_result.begin(), lower_result.end(), lower_result.begin(), ::tolower);
    
    for (const auto& mapping : known_mappings) {
        if (lower_result.find(mapping.first) != std::string::npos) {
            return mapping.second;
        }
    }
    
    return result.empty() ? raw_label : result;
}

std::string UIJsonNormalizerImpl::detect_control_type(const json& node) {
    std::string current_type = node.value("type", "");
    
    // Check for specific type indicators
    if (node.contains("checked") || current_type == "checkbox") {
        return "checkbox";
    }
    
    if (node.contains("value") && node.contains("vmin") && node.contains("vmax")) {
        return "slider";
    }
    
    if (node.contains("options") || node.contains("selected_value") || 
        is_combo_like(node)) {
        return "combo";
    }
    
    if (node.contains("state_open") || node.contains("state_selected") ||
        is_header_like(node)) {
        return "header";
    }
    
    if (node.contains("actions")) {
        auto actions = node["actions"];
        if (actions.is_array() && actions.size() > 0) {
            for (const auto& action : actions) {
                if (action == "drag") return "slider";
                if (action == "open" || action == "select") return "combo";
            }
            if (actions[0] == "click" && actions.size() == 1) {
                return is_button_like(node) ? "button" : "selectable";
            }
        }
    }
    
    // Keep existing type if it seems reasonable
    if (current_type == "button" || current_type == "window" || 
        current_type == "popup" || current_type == "tooltip" ||
        current_type == "selectable" || current_type == "input_text" ||
        current_type == "color" || current_type == "label") {
        return current_type;
    }
    
    return "custom";
}

bool UIJsonNormalizerImpl::is_container_type(const std::string& type) {
    return type == "window" || type == "window.auto" || 
           type == "popup" || type == "popup_window" ||
           type == "tooltip" || type == "tooltip_window" ||
           type == "child" || type == "scrollbar";
}

bool UIJsonNormalizerImpl::is_combo_like(const json& node) {
    if (node.contains("label_norm") || node.contains("label_raw")) {
        std::string label = node.value("label_norm", node.value("label_raw", ""));
        std::string lower_label = label;
        std::transform(lower_label.begin(), lower_label.end(), lower_label.begin(), ::tolower);
        
        return lower_label.find("resolution") != std::string::npos ||
               lower_label.find("fps") != std::string::npos ||
               lower_label.find("format") != std::string::npos ||
               lower_label.find("preset") != std::string::npos ||
               lower_label.find("mode") != std::string::npos;
    }
    return false;
}

bool UIJsonNormalizerImpl::is_button_like(const json& node) {
    if (node.contains("label_norm") || node.contains("label_raw")) {
        std::string label = node.value("label_norm", node.value("label_raw", ""));
        std::string lower_label = label;
        std::transform(lower_label.begin(), lower_label.end(), lower_label.begin(), ::tolower);
        
        return lower_label.find("save") != std::string::npos ||
               lower_label.find("load") != std::string::npos ||
               lower_label.find("restore") != std::string::npos ||
               lower_label.find("apply") != std::string::npos ||
               lower_label.find("record") != std::string::npos ||
               lower_label.find("start") != std::string::npos ||
               lower_label.find("stop") != std::string::npos;
    }
    return false;
}

bool UIJsonNormalizerImpl::is_header_like(const json& node) {
    if (node.contains("label_norm") || node.contains("label_raw")) {
        std::string label = node.value("label_norm", node.value("label_raw", ""));
        std::string lower_label = label;
        std::transform(lower_label.begin(), lower_label.end(), lower_label.begin(), ::tolower);
        
        return lower_label.find("controls") != std::string::npos ||
               lower_label.find("advanced") != std::string::npos ||
               lower_label.find("post") != std::string::npos ||
               lower_label.find("processing") != std::string::npos ||
               lower_label.find("options") != std::string::npos;
    }
    return false;
}

void UIJsonNormalizerImpl::calculate_visibility_state(json& node, const json& display, const json& containers) {
    if (!node.contains("bbox") || !node["bbox"].is_array() || node["bbox"].size() < 4) {
        node["onscreen"] = true;
        node["visible_area"] = 1.0;
        node["offscreen_reason"] = "";
        return;
    }
    
    auto bbox = node["bbox"];
    float x = bbox[0], y = bbox[1], w = bbox[2], h = bbox[3];
    float x2 = x + w, y2 = y + h;
    
    // Get display bounds
    float display_w = display.is_array() && display.size() >= 2 ? display[0] : 1920;
    float display_h = display.is_array() && display.size() >= 2 ? display[1] : 1080;
    
    // Calculate intersection with display
    float intersect_x1 = std::max(0.0f, x);
    float intersect_y1 = std::max(0.0f, y);
    float intersect_x2 = std::min(display_w, x2);
    float intersect_y2 = std::min(display_h, y2);
    
    if (intersect_x2 <= intersect_x1 || intersect_y2 <= intersect_y1) {
        // No intersection
        node["onscreen"] = false;
        node["visible_area"] = 0.0;
        
        if (x2 < 0) node["offscreen_reason"] = "left";
        else if (x > display_w) node["offscreen_reason"] = "right";
        else if (y2 < 0) node["offscreen_reason"] = "above";
        else if (y > display_h) node["offscreen_reason"] = "below";
        else node["offscreen_reason"] = "hidden";
    } else {
        // Partial or full intersection
        float intersect_area = (intersect_x2 - intersect_x1) * (intersect_y2 - intersect_y1);
        float total_area = w * h;
        float visible_ratio = total_area > 0 ? intersect_area / total_area : 1.0;
        
        node["onscreen"] = visible_ratio > 0.1; // Consider visible if >10% shown
        node["visible_area"] = visible_ratio;
        node["offscreen_reason"] = visible_ratio >= 1.0 ? "" : "partially_offscreen";
    }
}

std::vector<UIJsonNormalizerImpl::ComboInfo> UIJsonNormalizerImpl::detect_combo_popup_groups(const json& nodes) {
    std::vector<ComboInfo> combo_groups;
    
    for (size_t i = 0; i < nodes.size(); ++i) {
        const auto& node = nodes[i];
        
        if (node.value("type", "") == "combo" || is_combo_like(node)) {
            ComboInfo info;
            info.combo_index = i;
            info.popup_index = SIZE_MAX;
            
            uint64_t combo_id = node.value("id", 0ULL);
            
            // Look for associated popup
            for (size_t j = 0; j < nodes.size(); ++j) {
                const auto& candidate = nodes[j];
                if ((candidate.value("type", "") == "popup" || 
                     candidate.value("type", "") == "popup_window") &&
                    candidate.value("owner_id", 0ULL) == combo_id) {
                    info.popup_index = j;
                    break;
                }
            }
            
            // Look for option nodes
            for (size_t j = 0; j < nodes.size(); ++j) {
                const auto& candidate = nodes[j];
                if (candidate.value("type", "") == "selectable" &&
                    candidate.value("owner_id", 0ULL) == combo_id) {
                    info.option_indices.push_back(j);
                }
            }
            
            combo_groups.push_back(info);
        }
    }
    
    return combo_groups;
}

void UIJsonNormalizerImpl::normalize_combo_group(json& nodes, const ComboInfo& combo_info) {
    auto& combo = nodes[combo_info.combo_index];
    
    // Normalize combo
    combo["type"] = "combo";
    if (!combo.contains("actions") || combo["actions"].empty()) {
        combo["actions"] = json::array({"open", "select"});
    }
    
    // Set selected_value from options if available
    if (!combo.contains("selected_value") && !combo_info.option_indices.empty()) {
        for (size_t opt_idx : combo_info.option_indices) {
            const auto& option = nodes[opt_idx];
            if (option.value("state_selected", false)) {
                combo["selected_value"] = option.value("label_norm", 
                                                      option.value("label_raw", ""));
                break;
            }
        }
    }
    
    // Build options array
    if (!combo.contains("options") && !combo_info.option_indices.empty()) {
        json options_array = json::array();
        for (size_t opt_idx : combo_info.option_indices) {
            const auto& option = nodes[opt_idx];
            std::string opt_text = option.value("label_norm", 
                                               option.value("label_raw", ""));
            if (!opt_text.empty()) {
                options_array.push_back(opt_text);
            }
        }
        combo["options"] = options_array;
    }
    
    // Normalize popup if exists
    if (combo_info.popup_index != SIZE_MAX) {
        auto& popup = nodes[combo_info.popup_index];
        popup["type"] = "popup";
        popup["owner_id"] = combo.value("id", 0ULL);
        
        // Ensure popup has higher z_index than combo
        int combo_z = combo.value("z_index", 0);
        popup["z_index"] = combo_z + 10;
    }
    
    // Normalize options
    for (size_t opt_idx : combo_info.option_indices) {
        auto& option = nodes[opt_idx];
        option["type"] = "selectable";
        if (!option.contains("actions") || option["actions"].empty()) {
            option["actions"] = json::array({"click"});
        }
    }
}

void UIJsonNormalizerImpl::fix_container_references(json& nodes) {
    for (auto& node : nodes) {
        if (!node.contains("container_id")) continue;
        
        uint64_t container_id = node["container_id"];
        if (container_id == 0) continue; // Root is always valid
        
        // Check if container_id refers to a valid container
        if (container_ids_.find(container_id) == container_ids_.end()) {
            // Invalid container reference - find nearest valid container
            uint64_t node_id = node.value("id", 0ULL);
            uint64_t new_container = find_nearest_container(node_id, nodes);
            node["container_id"] = new_container;
        }
    }
}

uint64_t UIJsonNormalizerImpl::find_nearest_container(uint64_t node_id, const json& nodes) {
    // For now, just assign to the first window container we find
    // In a more sophisticated implementation, we'd use spatial proximity
    for (const auto& node : nodes) {
        if (node.contains("id") && node.contains("type")) {
            uint64_t id = node["id"];
            std::string type = node["type"];
            if (is_container_type(type) && container_ids_.count(id)) {
                return id;
            }
        }
    }
    return 0; // Fallback to root
}

void UIJsonNormalizerImpl::assign_z_indices_by_category(json& nodes) {
    std::vector<ZIndexGroup> groups = {
        {"window", 1, {}},
        {"child", 5, {}},
        {"popup", 10, {}},
        {"tooltip", 20, {}},
        {"overlay", 30, {}}
    };
    
    // Categorize nodes
    for (size_t i = 0; i < nodes.size(); ++i) {
        const auto& node = nodes[i];
        std::string type = node.value("type", "");
        
        if (type == "window") {
            groups[0].node_indices.push_back(i);
        } else if (type == "child") {
            groups[1].node_indices.push_back(i);
        } else if (type == "popup") {
            groups[2].node_indices.push_back(i);
        } else if (type == "tooltip") {
            groups[3].node_indices.push_back(i);
        } else if (node.value("container_id", 0ULL) == 0) {
            // Top-level element
            groups[4].node_indices.push_back(i);
        }
    }
    
    // Assign z-indices within groups
    for (const auto& group : groups) {
        int z_index = group.base_priority;
        for (size_t node_idx : group.node_indices) {
            nodes[node_idx]["z_index"] = z_index++;
        }
    }
}

bool UIJsonNormalizerImpl::validate_normalized_json(const json& json_obj) {
    validation_errors_.clear();
    
    // Check version
    if (json_obj.value("ui_version", "") != "1.2.0") {
        validation_errors_.push_back("ui_version must be 1.2.0");
    }
    
    // Check nodes array
    if (!json_obj.contains("nodes") || !json_obj["nodes"].is_array()) {
        validation_errors_.push_back("nodes array is required");
        return false;
    }
    
    const auto& nodes = json_obj["nodes"];
    
    // Validate each node
    for (size_t i = 0; i < nodes.size(); ++i) {
        const auto& node = nodes[i];
        std::string prefix = "Node " + std::to_string(i) + ": ";
        
        // Required fields
        if (!node.contains("onscreen")) {
            validation_errors_.push_back(prefix + "missing onscreen field");
        }
        if (!node.contains("visible_area")) {
            validation_errors_.push_back(prefix + "missing visible_area field");
        }
        if (!node.contains("offscreen_reason")) {
            validation_errors_.push_back(prefix + "missing offscreen_reason field");
        }
        if (!node.contains("z_index")) {
            validation_errors_.push_back(prefix + "missing z_index field");
        }
        if (!node.contains("container_id")) {
            validation_errors_.push_back(prefix + "missing container_id field");
        }
        
        // Validate container reference
        uint64_t container_id = node.value("container_id", 0ULL);
        if (container_id != 0 && container_ids_.find(container_id) == container_ids_.end()) {
            validation_errors_.push_back(prefix + "invalid container_id reference");
        }
    }
    
    return validation_errors_.empty();
}

// Standalone utility functions
std::string normalize_ui_json_file(const std::string& input_file_path, 
                                  const std::string& output_file_path) {
    std::ifstream file(input_file_path);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open input file: " + input_file_path);
    }
    
    std::stringstream buffer;
    buffer << file.rdbuf();
    std::string input_json = buffer.str();
    
    UIJsonNormalizer normalizer;
    std::string normalized_json = normalizer.normalize_json_string(input_json);
    
    std::string output_path = output_file_path.empty() ? 
        (input_file_path + ".normalized.json") : output_file_path;
    
    std::ofstream output_file(output_path);
    if (!output_file.is_open()) {
        throw std::runtime_error("Cannot create output file: " + output_path);
    }
    
    output_file << normalized_json;
    return output_path;
}

bool validate_ui_json_v1_2(const std::string& json_file_path) {
    try {
        std::ifstream file(json_file_path);
        if (!file.is_open()) return false;
        
        std::stringstream buffer;
        buffer << file.rdbuf();
        
        json json_obj = json::parse(buffer.str());
        
        UIJsonNormalizer normalizer;
        return normalizer.validate_normalized_json(json_obj);
    } catch (...) {
        return false;
    }
}
