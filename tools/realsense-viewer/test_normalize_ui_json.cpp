#include "json_normalizer.h"
#include <iostream>
#include <fstream>

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: " << argv[0] << " <input.json> <output.json>" << std::endl;
        return 1;
    }

    // Read input file
    std::ifstream input(argv[1]);
    if (!input) {
        std::cerr << "Error: Could not open input file " << argv[1] << std::endl;
        return 1;
    }

    std::string json_content((std::istreambuf_iterator<char>(input)),
                             std::istreambuf_iterator<char>());
    input.close();

    try {
        // Normalize the JSON
        std::string normalized = normalize_ui_json_to_v1_2(json_content);

        // Write output file
        std::ofstream output(argv[2]);
        if (!output) {
            std::cerr << "Error: Could not create output file " << argv[2] << std::endl;
            return 1;
        }

        output << normalized;
        output.close();

        std::cout << "Successfully normalized " << argv[1] << " -> " << argv[2] << std::endl;
        std::cout << "Version: v1.2.0" << std::endl;

        // Validate the result
        if (validate_ui_json_v1_2(normalized)) {
            std::cout << "Validation: PASSED" << std::endl;
        } else {
            std::cout << "Validation: FAILED" << std::endl;
            return 1;
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
