#!/usr/bin/env python3
# License: Apache 2.0. See LICENSE file in root directory.
# Copyright(c) 2023 RealSense, Inc. All Rights Reserved.

"""
General RealSense Viewer Test Runner
====================================

This script provides a general test runner for RealSense Viewer tests that are defined
in JSON format. It can:
- Discover and run all JSON test files in the tests/ directory
- Run specific tests by name
- Execute test sequences defined in JSON files
- Validate test results based on test configuration

Usage:
    python general_viewer_test_runner.py [test_name]
    
    If no test_name is provided, it will run all tests found in the tests/ directory.
    
Test JSON Format:
    {
        "name": "Test Name",
        "description": "Test description",
        "enabled": true,  // Optional, default: true - whether test is enabled
        "device_requirements": ["D455", "D435i"],  // Optional device requirements
        "task_description": "Description of what agent should do",
        "window_setup": "fullscreen|normal|maximized",  // Optional, default: fullscreen
        "timeout_seconds": 120,  // Optional, default: 120
        "validation": {
            "type": "agent_result|custom",
            "expect_success": true,
            "required_keywords": ["keyword1", "keyword2"]  // Optional
        },
        "sequence": [  // Optional - for multi-step tests
            {
                "type": "task",
                "prompt": "action description",
                "name": "Step name"
            },
            {
                "type": "validate", 
                "expectation": "validation description",
                "mode": "validation_mode"
            }
        ]
    }
"""

import sys
import os
import json
import glob
import argparse
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from rspy import test, log, repo
from agent_server_client import AgentServerClient
from viewer_process_manager import ViewerProcessManager 
from gui_server_manager import GuiServerManager, setup_ci_environment
from test_constants import HttpStatusCode, TestTiming, WindowSetupMode, TestDefaults, ValidationPresets

class ViewerTestRunner:
    """General test runner for RealSense Viewer tests defined in JSON format."""
    
    def __init__(self):
        self.tests_dir = Path(__file__).parent / "tests"
        self.viewer_mgr = None
        self.gui_server = None
        self.agent_client = None
        self.rs_viewer_exe = None
        
    def find_viewer_executable(self):
        """Find the realsense-viewer executable."""
        import platform
        import shutil
        
        exe_name = 'realsense-viewer.exe' if platform.system() == 'Windows' else 'realsense-viewer'
        
        # Try repo finder first
        rs_viewer_exe = repo.find_built_exe('tools/realsense-viewer', 'realsense-viewer')
        if not rs_viewer_exe:
            rs_viewer_exe = shutil.which(exe_name)
        
        if not rs_viewer_exe:
            log.e(f'no {exe_name} was found!')
            log.e('On Windows: Make sure RealSense SDK is built and realsense-viewer.exe is in your PATH or built directory')
            log.e('On Linux: Make sure RealSense SDK is built with DBUILD_TOOLS=ON')
            return None
            
        log.d(f'Found realsense-viewer at: {rs_viewer_exe}')
        self.rs_viewer_exe = rs_viewer_exe
        return rs_viewer_exe
    
    def load_test_file(self, test_file_path):
        """Load and validate a test JSON file."""
        try:
            with open(test_file_path, 'r') as f:
                test_data = json.load(f)
            
            # Validate required fields
            required_fields = ['name', 'task_description']
            for field in required_fields:
                if field not in test_data:
                    log.e(f"Test file {test_file_path} missing required field: {field}")
                    return None
                    
            # Set defaults
            test_data.setdefault('enabled', True)
            test_data.setdefault('window_setup', TestDefaults.DEFAULT_WINDOW_SETUP)
            test_data.setdefault('timeout_seconds', TestDefaults.DEFAULT_TEST_TIMEOUT_SECONDS)
            test_data.setdefault('validation', {'type': 'agent_result', 'expect_success': True})
            
            return test_data
            
        except json.JSONDecodeError as e:
            log.e(f"Failed to parse JSON file {test_file_path}: {e}")
            return None
        except Exception as e:
            log.e(f"Failed to load test file {test_file_path}: {e}")
            return None
    
    def discover_tests(self):
        """Discover all JSON test files in the tests directory."""
        if not self.tests_dir.exists():
            log.w(f"Tests directory {self.tests_dir} does not exist")
            return []
        
        test_files = list(self.tests_dir.glob("*.json"))
        tests = []
        
        for test_file in test_files:
            test_data = self.load_test_file(test_file)
            if test_data:
                test_data['_file_path'] = str(test_file)
                test_data['_file_name'] = test_file.stem
                # Only include enabled tests
                if test_data.get('enabled', True):
                    tests.append(test_data)
                else:
                    log.d(f"Skipping disabled test: {test_data['name']}")
                
        return tests
    
    def setup_test_environment(self):
        """Setup the test environment with viewer, GUI server, and agent client."""
        setup_ci_environment()
        
        if not self.find_viewer_executable():
            return False
        
        # Initialize components
        self.viewer_mgr = ViewerProcessManager(exe_path=self.rs_viewer_exe)
        self.gui_server = GuiServerManager()
        self.agent_client = AgentServerClient()
        
        return True
    
    def get_window_setup_mode(self, setup_mode_str):
        """Convert string window setup mode to enum."""
        mode_map = {
            'fullscreen': WindowSetupMode.FULLSCREEN,
            'normal': WindowSetupMode.NORMAL,
            'maximized': WindowSetupMode.MAXIMIZED
        }
        return mode_map.get(setup_mode_str.lower(), WindowSetupMode.FULLSCREEN)
    
    def run_single_task_test(self, test_data):
        """Run a single task test (non-sequence)."""
        log.i(f"Running single task test: {test_data['name']}")
        
        try:
            # 1) Launch and wait for GUI control server
            test.check(self.gui_server.start())

            # 2) Start RealSense Viewer
            viewer_process = self.viewer_mgr.start()
            log.i('realsense-viewer started with PID:', viewer_process.pid)

            # 3) Setup viewer window
            window_mode = self.get_window_setup_mode(test_data['window_setup'])
            self.gui_server.setup_viewer_window(mode=window_mode, logger_func=log.i)

            # 4) Agent health check
            health_body, health_code = self.agent_client.health_check()
            log.i('Agent health check result:', f'code={health_code}, body={health_body}')
            test.check(health_code == HttpStatusCode.OK)

            # 5) Get GUI URL reachable from agent host
            gui_url = self.gui_server.get_gui_url_for_host(self.agent_client.host)
            log.i('GUI control URL (agent will call this):', gui_url)

            # 6) Run agent task
            self.agent_client.custom_task = self.agent_client.build_task_with_os(
                test_data['task_description'], 
                gui_url, 
                self.gui_server
            )
            
            result_body, result_code = self.agent_client.start_run()
            test.check(result_code in (HttpStatusCode.OK, HttpStatusCode.ACCEPTED))
            
            # 7) Parse and validate result
            result_data = self.agent_client.validate_and_log_result(result_body, log.i)
            
            # 8) Apply test-specific validation
            success = self.validate_test_result(test_data, result_data)
            
            return success
            
        except Exception as e:
            log.e(f"Test {test_data['name']} failed with exception: {e}")
            return False
    
    def run_sequence_test(self, test_data):
        """Run a sequence-based test with multiple steps."""
        log.i(f"Running sequence test: {test_data['name']} with {len(test_data['sequence'])} steps")
        
        try:
            # Setup environment similar to single task test
            test.check(self.gui_server.start())
            viewer_process = self.viewer_mgr.start()
            log.i('realsense-viewer started with PID:', viewer_process.pid)
            
            window_mode = self.get_window_setup_mode(test_data['window_setup'])
            self.gui_server.setup_viewer_window(mode=window_mode, logger_func=log.i)
            
            health_body, health_code = self.agent_client.health_check()
            test.check(health_code == HttpStatusCode.OK)
            
            gui_url = self.gui_server.get_gui_url_for_host(self.agent_client.host)
            
            # Execute sequence steps
            for i, step in enumerate(test_data['sequence']):
                log.i(f"Executing step {i+1}: {step.get('name', f'Step {i+1}')}")
                
                if step['type'] == 'task':
                    # Execute a task step
                    self.agent_client.custom_task = self.agent_client.build_task_with_os(
                        step['prompt'], 
                        gui_url, 
                        self.gui_server
                    )
                    
                    result_body, result_code = self.agent_client.start_run()
                    test.check(result_code in (HttpStatusCode.OK, HttpStatusCode.ACCEPTED))
                    
                    result_data = self.agent_client.validate_and_log_result(result_body, log.i)
                    if not result_data.get('success', False):
                        log.e(f"Task step {i+1} failed")
                        return False
                        
                elif step['type'] == 'validate':
                    # Execute a validation step
                    validation_task = f"Validate that: {step['expectation']}"
                    if 'mode' in step:
                        validation_task += f" (validation mode: {step['mode']})"
                    
                    self.agent_client.custom_task = self.agent_client.build_task_with_os(
                        validation_task, 
                        gui_url, 
                        self.gui_server
                    )
                    
                    result_body, result_code = self.agent_client.start_run()
                    test.check(result_code in (HttpStatusCode.OK, HttpStatusCode.ACCEPTED))
                    
                    result_data = self.agent_client.validate_and_log_result(result_body, log.i)
                    if not result_data.get('success', False):
                        log.e(f"Validation step {i+1} failed")
                        return False
                        
                else:
                    log.w(f"Unknown step type: {step['type']}")
                    
                # Small delay between steps
                time.sleep(1)
            
            return True
            
        except Exception as e:
            log.e(f"Sequence test {test_data['name']} failed with exception: {e}")
            return False
    
    def validate_test_result(self, test_data, result_data):
        """Validate test results based on test configuration."""
        validation = test_data.get('validation', {})
        
        if validation.get('type') == 'agent_result':
            # Standard agent result validation
            success = result_data.get('success', False)
            
            if validation.get('expect_success', True):
                if not success:
                    log.e(f"Test expected success but got failure - ok: {result_data.get('ok')}, passed: {result_data.get('passed')}, exit_code: {result_data.get('exit_code')}")
                    return False
            else:
                if success:
                    log.e("Test expected failure but got success")
                    return False
            
            # Check for required keywords in result
            if 'required_keywords' in validation:
                result_text = str(result_data).lower()
                for keyword in validation['required_keywords']:
                    if keyword.lower() not in result_text:
                        log.e(f"Required keyword '{keyword}' not found in result")
                        return False
                        
            return success
            
        elif validation.get('type') == 'custom':
            # Custom validation logic could be added here
            log.w("Custom validation not implemented yet")
            return result_data.get('success', False)
            
        else:
            # Default: just check success
            return result_data.get('success', False)
    
    def run_test(self, test_data):
        """Run a single test (either single task or sequence)."""
        test_name = test_data['name']
        log.i(f"Starting test: {test_name}")
        log.i(f"Description: {test_data.get('description', 'No description')}")
        
        with test.closure(f"Test: {test_name}"):
            try:
                if 'sequence' in test_data:
                    success = self.run_sequence_test(test_data)
                else:
                    success = self.run_single_task_test(test_data)
                    
                if success:
                    log.i(f"✓ Test {test_name} PASSED")
                else:
                    log.e(f"✗ Test {test_name} FAILED")
                    
                return success
                
            finally:
                # Clean up components
                if self.viewer_mgr:
                    self.viewer_mgr.cleanup()
                if self.gui_server:
                    self.gui_server.cleanup()
    
    def run_all_tests(self, test_filter=None):
        """Run all discovered tests, optionally filtering by name."""
        tests = self.discover_tests()
        
        if not tests:
            log.w("No tests discovered")
            return True
        
        if test_filter:
            tests = [t for t in tests if test_filter.lower() in t['name'].lower() or test_filter == t['_file_name']]
            if not tests:
                log.e(f"No tests found matching filter: {test_filter}")
                return False
        
        log.i(f"Discovered {len(tests)} test(s)")
        
        if not self.setup_test_environment():
            log.e("Failed to setup test environment")
            return False
        
        passed = 0
        failed = 0
        
        for test_data in tests:
            try:
                if self.run_test(test_data):
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                log.e(f"Test {test_data['name']} failed with exception: {e}")
                failed += 1
        
        log.i(f"Test Results: {passed} passed, {failed} failed")
        return failed == 0

def main():
    parser = argparse.ArgumentParser(description='RealSense Viewer Test Runner')
    parser.add_argument('test_name', nargs='?', help='Name of specific test to run (optional)')
    parser.add_argument('--list', action='store_true', help='List all available tests')
    parser.add_argument('--tests-dir', default=None, help='Custom tests directory path')
    
    args = parser.parse_args()
    
    runner = ViewerTestRunner()
    
    if args.tests_dir:
        runner.tests_dir = Path(args.tests_dir)
    
    if args.list:
        tests = runner.discover_tests()
        if tests:
            log.i("Available tests:")
            for test_data in tests:
                log.i(f"  - {test_data['_file_name']}: {test_data['name']}")
        else:
            log.i("No tests found")
        return
    
    success = runner.run_all_tests(args.test_name)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
