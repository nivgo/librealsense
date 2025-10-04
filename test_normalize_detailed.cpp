#include "tools/realsense-viewer/json_normalizer.h"
#include <iostream>
#include <string>
#include <fstream>

int main() {
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
        std::string normalized = normalize_ui_json_to_v1_2(test_json);
        
        std::ofstream out("normalized_output.json");
        out << normalized;
        out.close();
        
        std::cout << "Wrote normalized JSON to normalized_output.json" << std::endl;
        std::cout << "Size: " << normalized.length() << " bytes" << std::endl;
        
        return 0;
    } catch (const std::exception& e) {
        std::cout << "Error: " << e.what() << std::endl;
        return 1;
    }
}
