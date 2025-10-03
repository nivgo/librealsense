#!/usr/bin/env python3

import re
import sys

def fix_rs_log_last(content):
    """Fix RS_LOG_LAST calls with complex string concatenation"""
    
    # Pattern to match RS_LOG_LAST calls with "info" and complex string concatenation
    pattern = r'RS_LOG_LAST\("info",\s*\n\s*"([^"]+)"\s*<<\s*([^)]+)\);'
    
    def replacement(match):
        prefix = match.group(1)
        rest = match.group(2)
        # Create a std::string log_msg and use it
        return f'''std::string log_msg = rsutils::string::from() << "{prefix}" << {rest};
                RS_LOG_LAST("treenode", log_msg.c_str());'''
    
    # Apply the replacement
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Fix simple string literal cases
    content = re.sub(r'RS_LOG_LAST\("info",\s*\n\s*"([^"<>]+)"\);', 
                     lambda m: f'RS_LOG_LAST("treenode", "{m.group(1)}");', 
                     content, flags=re.MULTILINE)
    
    return content

def main():
    # Read the file
    with open('/home/administrator/librealsense_uishift/common/device-model.cpp', 'r') as f:
        content = f.read()
    
    # Apply fixes
    fixed_content = fix_rs_log_last(content)
    
    # Write back
    with open('/home/administrator/librealsense_uishift/common/device-model.cpp', 'w') as f:
        f.write(fixed_content)
    
    print("Fixed RS_LOG_LAST calls in device-model.cpp")

if __name__ == "__main__":
    main()
