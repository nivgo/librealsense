#pragma once

#include <string>
#include <vector>
#include <set>
#include <map>

// Use an opaque pointer approach to avoid including heavy nlohmann/json in header
class UIJsonNormalizerImpl;

/**
 * @brief 8-stage normalization pipeline for UI JSON dumps
 * 
 * Processes any UI JSON dump to produce normalized v1.2.0 format with:
 * - Correct hierarchy and container relationships
 * - Properly typed controls (button, slider, combo, etc.)
 * - Human-readable labels
 * - Complete state fields (visible, enabled, aliases, etc.)
 * - Z-order indexing
 * - Combo/popup relationship detection
 */
class UIJsonNormalizer {
public:
    struct NormalizationOptions {
        bool preserve_original_ids;
        bool auto_detect_combos;
        bool fix_container_hierarchy;
        bool normalize_labels;
        bool deduplicate_nodes;
        bool assign_z_indices;
        bool validate_output;
        
        NormalizationOptions() 
            : preserve_original_ids(true)
            , auto_detect_combos(true)
            , fix_container_hierarchy(true)
            , normalize_labels(true)
            , deduplicate_nodes(true)
            , assign_z_indices(true)
            , validate_output(true)
        {}
    };

    explicit UIJsonNormalizer(const NormalizationOptions& opts);
    UIJsonNormalizer(); // Default constructor
    ~UIJsonNormalizer();

    // Main public API
    std::string normalize_json_string(const std::string& json_string);

private:
    UIJsonNormalizerImpl* impl_; // Pimpl idiom to hide JSON dependency
};

// Standalone functions for external use
std::string normalize_ui_json_to_v1_2(const std::string& json_string);
bool validate_ui_json_v1_2(const std::string& json_string);
