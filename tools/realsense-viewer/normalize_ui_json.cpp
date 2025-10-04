#include "json_normalizer.h"
#include <iostream>
#include <filesystem>
#include <chrono>

void print_usage() {
    std::cout << "UI JSON Normalizer - Convert any UI dump to v1.2.0 format\n\n";
    std::cout << "Usage:\n";
    std::cout << "  normalize_ui_json <input.json> [output.json]\n";
    std::cout << "  normalize_ui_json --validate <file.json>\n";
    std::cout << "  normalize_ui_json --batch <directory>\n\n";
    std::cout << "Options:\n";
    std::cout << "  --validate   Validate JSON against v1.2.0 schema\n";
    std::cout << "  --batch      Process all .json files in directory\n";
    std::cout << "  --help       Show this help message\n\n";
    std::cout << "Examples:\n";
    std::cout << "  normalize_ui_json ui_dump_001.json\n";
    std::cout << "  normalize_ui_json input.json output_normalized.json\n";
    std::cout << "  normalize_ui_json --validate normalized.json\n";
    std::cout << "  normalize_ui_json --batch ./ui_dumps/\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        print_usage();
        return 1;
    }
    
    std::string command = argv[1];
    
    if (command == "--help" || command == "-h") {
        print_usage();
        return 0;
    }
    
    try {
        if (command == "--validate") {
            if (argc < 3) {
                std::cerr << "Error: --validate requires a file path\n";
                return 1;
            }
            
            std::string file_path = argv[2];
            bool is_valid = validate_ui_json_v1_2(file_path);
            
            if (is_valid) {
                std::cout << "✓ " << file_path << " is valid v1.2.0 JSON\n";
                return 0;
            } else {
                std::cout << "✗ " << file_path << " is not valid v1.2.0 JSON\n";
                return 1;
            }
        }
        else if (command == "--batch") {
            if (argc < 3) {
                std::cerr << "Error: --batch requires a directory path\n";
                return 1;
            }
            
            std::string dir_path = argv[2];
            if (!std::filesystem::exists(dir_path) || !std::filesystem::is_directory(dir_path)) {
                std::cerr << "Error: Directory does not exist: " << dir_path << "\n";
                return 1;
            }
            
            int processed = 0;
            int errors = 0;
            
            for (const auto& entry : std::filesystem::directory_iterator(dir_path)) {
                if (entry.path().extension() == ".json") {
                    try {
                        std::string input_path = entry.path().string();
                        std::string output_path = entry.path().stem().string() + "_normalized.json";
                        output_path = (std::filesystem::path(dir_path) / output_path).string();
                        
                        auto start = std::chrono::high_resolution_clock::now();
                        std::string result_path = normalize_ui_json_file(input_path, output_path);
                        auto end = std::chrono::high_resolution_clock::now();
                        
                        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
                        
                        std::cout << "✓ Normalized " << entry.path().filename() 
                                  << " -> " << std::filesystem::path(result_path).filename()
                                  << " (" << duration.count() << "ms)\n";
                        processed++;
                    } catch (const std::exception& e) {
                        std::cerr << "✗ Error processing " << entry.path().filename() 
                                  << ": " << e.what() << "\n";
                        errors++;
                    }
                }
            }
            
            std::cout << "\nBatch processing complete:\n";
            std::cout << "  Processed: " << processed << " files\n";
            std::cout << "  Errors: " << errors << " files\n";
            return errors > 0 ? 1 : 0;
        }
        else {
            // Single file normalization
            std::string input_path = argv[1];
            std::string output_path = argc >= 3 ? argv[2] : "";
            
            if (!std::filesystem::exists(input_path)) {
                std::cerr << "Error: Input file does not exist: " << input_path << "\n";
                return 1;
            }
            
            auto start = std::chrono::high_resolution_clock::now();
            std::string result_path = normalize_ui_json_file(input_path, output_path);
            auto end = std::chrono::high_resolution_clock::now();
            
            auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
            
            std::cout << "✓ Successfully normalized UI JSON\n";
            std::cout << "  Input:  " << input_path << "\n";
            std::cout << "  Output: " << result_path << "\n";
            std::cout << "  Time:   " << duration.count() << "ms\n";
            
            // Validate the result
            if (validate_ui_json_v1_2(result_path)) {
                std::cout << "  Status: Valid v1.2.0 JSON ✓\n";
            } else {
                std::cout << "  Status: Validation failed ✗\n";
                return 1;
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
    
    return 0;
}
