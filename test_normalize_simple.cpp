#include "json_normalizer.h"
#include <iostream>
#include <string>

int main() {
    // Test JSON string
    std::string test_json = R"({
  "ui_version": "1.1.0",
  "app_version": "2.50.0",
  "frame": 123,
  "frame_ts": 1234567890.123,
  "display": [1920, 1080],
  "input_event": {"type":"none","data":0},
  "containers": {
    "100": {
      "scroll": [0, 0],
      "scroll_max": [0, 100],
      "content": [800, 600],
      "size": [800, 600]
    }
  },
  "nodes": [
    {
      "id": 1,
      "type": "button",
      "label_raw": "start_button##001",
      "bbox": [10, 10, 100, 30],
      "container_id": 100,
      "onscreen": true,
      "visible_area": 1.0
    },
    {
      "id": 2,
      "type": "control",
      "label_raw": "exposure_slider_ctrl",
      "bbox": [10, 50, 200, 20],
      "container_id": 100,
      "onscreen": true,
      "visible_area": 1.0,
      "value": 50.0,
      "vmin": 0.0,
      "vmax": 100.0
    },
    {
      "id": 3,
      "type": "unknown",
      "label_raw": "resolution_combo###dropdown",
      "bbox": [10, 80, 150, 25],
      "container_id": 100,
      "onscreen": true,
      "visible_area": 1.0
    }
  ]
})";

    try {
        std::cout << "=== Testing UI JSON Normalization to v1.2.0 ===" << std::endl;
        std::cout << "Input JSON size: " << test_json.length() << " bytes" << std::endl;
        
        // Test normalization
        std::string normalized = normalize_ui_json_to_v1_2(test_json);
        
        std::cout << "Normalized JSON size: " << normalized.length() << " bytes" << std::endl;
        std::cout << "Normalization: SUCCESS" << std::endl;
        
        // Test validation
        bool valid = validate_ui_json_v1_2(normalized);
        std::cout << "Validation: " << (valid ? "PASSED" : "FAILED") << std::endl;
        
        // Print a sample of the normalized output
        std::cout << std::endl << "=== Normalized JSON (first 500 chars) ===" << std::endl;
        std::string sample = normalized.substr(0, 500);
        std::cout << sample;
        if (normalized.length() > 500) {
            std::cout << "...";
        }
        std::cout << std::endl;
        
        return valid ? 0 : 1;
        
    } catch (const std::exception& e) {
        std::cout << "Error: " << e.what() << std::endl;
        return 1;
    }
}
