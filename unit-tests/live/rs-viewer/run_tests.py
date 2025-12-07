#!/usr/bin/env python3
# License: Apache 2.0. See LICENSE file in root directory.
# Copyright(c) 2023 RealSense, Inc. All Rights Reserved.

"""
Simple test runner entry point for RealSense Viewer tests.

This script provides a simple way to run viewer tests without needing to
understand the full command line interface of the general test runner.

Usage examples:
    python run_tests.py                           # Run all tests
    python run_tests.py stereo_depth_health       # Run specific test
    python run_tests.py resolution                # Run tests containing "resolution"
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    script_dir = Path(__file__).parent
    runner_script = script_dir / "general_viewer_test_runner.py"
    
    if not runner_script.exists():
        print(f"Error: {runner_script} not found!")
        sys.exit(1)
    
    # Pass all arguments to the general runner
    cmd = [sys.executable, str(runner_script)] + sys.argv[1:]
    
    try:
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
