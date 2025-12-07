#pragma once

#include <string>
#include <utility>
#include "json.hpp"

using json = nlohmann::json;

// Comprehensive JSON normalizer that addresses all the issues identified by the LLM
// This includes:
// - Float precision formatting to 3 decimals 
// - Enhanced label normalization with icon/debug token removal
// - Canonical label mapping for known UI elements
// - Proper tooltip/popup naming
// - Clean alias processing
std::string normalize_ui_json_to_v1_2_comprehensive(const std::string& json_string);

// GRPO format helper functions
std::string normalize_to_grpo_format(const std::string& json_str);
std::string normalize_label_text_grpo(const std::string& label_raw, const std::string& role, const std::string& icon_token);
std::string detect_icon_token_grpo(const std::string& label_raw, const std::string& role);
json extract_key_path_grpo(const std::string& label_raw);
int extract_count_grpo(const std::string& label_raw);
std::pair<std::string, std::string> extract_device_info_grpo(const std::string& label_raw);
