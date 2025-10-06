# License: Apache 2.0. See LICENSE file in root directory.
# Copyright(c) 2023 RealSense, Inc. All Rights Reserved.

# Stereo Viewer Health Test invoking external agent automation.

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from rspy import test, log, repo
from agent_server_client import AgentServerClient
from viewer_process_manager import ViewerProcessManager 
from gui_server_manager import GuiServerManager, setup_ci_environment
from test_constants import HttpStatusCode, TestTiming, WindowSetupMode
import time
import platform

#test:device each(D455) 
#test:donotrun:!agent-test

with test.closure("Stereo depth health scenario via agent server"):
    # Setup CI environment variables
    setup_ci_environment()
    
    # Log environment information for debugging
    log.i(f'Running on platform: {platform.system()}')
    log.i(f'Current working directory: {os.getcwd()}')
    log.i(f'DISPLAY environment: {os.environ.get("DISPLAY", "Not set")}')
    log.i(f'PATH: {os.environ.get("PATH", "Not set")[:200]}...')  # Truncate for readability
    log.i(f'Python executable: {sys.executable}')
    
    # Check if realsense-viewer executable exists (like test-enumerate-devices)
    import platform
    import shutil
    exe_name = 'realsense-viewer.exe' if platform.system() == 'Windows' else 'realsense-viewer'
    
    # Try repo finder first (without .exe extension, let repo.find_built_exe handle platform-specific naming)
    rs_viewer_exe = repo.find_built_exe('tools/realsense-viewer', 'realsense-viewer')
    if not rs_viewer_exe:
        rs_viewer_exe = shutil.which(exe_name)
    
    test.check(rs_viewer_exe)
    
    if not rs_viewer_exe:
        log.e(f'no {exe_name} was found!')
        log.e('On Windows: Make sure RealSense SDK is built and realsense-viewer.exe is in your PATH or built directory')
        log.e('On Linux: Make sure RealSense SDK is built with DBUILD_TOOLS=ON')
        import sys
        log.d('sys.path=\n    ' + '\n    '.join(sys.path))
    else:
        log.d(f'Found realsense-viewer at: {rs_viewer_exe}')
    
    # Initialize components
    viewer_mgr = ViewerProcessManager(exe_path=rs_viewer_exe)
    gui_server = GuiServerManager()
    agent_client = AgentServerClient()

    try:
        # 1) Launch and wait for GUI control server
        log.i('Starting GUI control server...')
        server_started = gui_server.start()
        log.i(f'GUI server start result: {server_started}')
        test.check(server_started)
        
        if server_started:
            log.i(f'GUI server running at: {gui_server.get_gui_url_for_host("localhost")}')
            
            # Test if server is responding to basic requests
            try:
                import requests
                test_url = gui_server.get_gui_url_for_host("localhost") + "/healthz"
                log.i(f'Testing GUI server health at: {test_url}')
                response = requests.get(test_url, timeout=5)
                log.i(f'GUI server health response: {response.status_code}')
                
                # Test screenshot endpoint specifically - CRITICAL DEBUG SECTION
                screenshot_url = gui_server.get_gui_url_for_host("localhost") + "/screenshot"
                log.i(f'[TEST_DEBUG] Testing screenshot endpoint at: {screenshot_url}')
                log.i(f'[TEST_DEBUG] Current environment: DISPLAY={os.environ.get("DISPLAY", "NOT_SET")}')
                
                # Test multiple times to catch intermittent issues
                for attempt in range(3):
                    log.i(f'[TEST_DEBUG] Screenshot attempt {attempt + 1}/3')
                    try:
                        screenshot_response = requests.get(screenshot_url, timeout=15)
                        log.i(f'[TEST_DEBUG] Screenshot attempt {attempt + 1} response: {screenshot_response.status_code}')
                        log.i(f'[TEST_DEBUG] Response headers: {dict(screenshot_response.headers)}')
                        log.i(f'[TEST_DEBUG] Content length: {len(screenshot_response.content)} bytes')
                        
                        if screenshot_response.status_code != 200:
                            log.e(f'[TEST_DEBUG] Screenshot attempt {attempt + 1} error: {screenshot_response.text[:500]}')
                        else:
                            log.i(f'[TEST_DEBUG] Screenshot attempt {attempt + 1} SUCCESS')
                            break  # Success, no need to retry
                    except Exception as screenshot_exc:
                        log.e(f'[TEST_DEBUG] Screenshot attempt {attempt + 1} exception: {screenshot_exc}')
                    
                    if attempt < 2:  # Don't sleep after last attempt
                        time.sleep(2)
                    
            except Exception as e:
                log.e(f'GUI server connectivity test failed: {e}')
                # Don't fail the test yet, continue to see what happens

        # 2) Start RealSense Viewer
        viewer_process = viewer_mgr.start()
        log.i('realsense-viewer started with PID:', viewer_process.pid)

        # 3) Setup viewer window
        gui_server.setup_viewer_window(mode=WindowSetupMode.FULLSCREEN, logger_func=log.i)

        # 4) Agent health check - is agent responding
        health_body, health_code = agent_client.health_check()
        log.i('Agent health check result:', f'code={health_code}, body={health_body}')
        log.i('Agent base URL:', agent_client.base_url)
        test.check(health_code == HttpStatusCode.OK)
        log.d('Agent health:', health_body)

        # 5) Get GUI URL reachable from agent host
        gui_url = gui_server.get_gui_url_for_host(agent_client.host)
        log.i('GUI control URL (agent will call this):', gui_url)
        
        # CRITICAL DEBUG: Test the exact URL the agent will use
        log.i(f'[TEST_DEBUG] Agent host: {agent_client.host}')
        log.i(f'[TEST_DEBUG] GUI URL for agent: {gui_url}')
        
        # Test if agent can reach the GUI URL (simulate what agent will do)
        try:
            import requests
            agent_test_url = gui_url + "/healthz"
            log.i(f'[TEST_DEBUG] Testing agent-reachable URL: {agent_test_url}')
            
            # Create session like agent would
            agent_session = requests.Session()
            agent_session.trust_env = False
            agent_session.proxies = {"http": None, "https": None}
            
            agent_health_resp = agent_session.get(agent_test_url, timeout=10)
            log.i(f'[TEST_DEBUG] Agent-reachable health check: {agent_health_resp.status_code}')
            
            # Test the critical screenshot endpoint from agent perspective
            agent_screenshot_url = gui_url + "/screenshot"
            log.i(f'[TEST_DEBUG] Testing agent-reachable screenshot: {agent_screenshot_url}')
            agent_screenshot_resp = agent_session.get(agent_screenshot_url, timeout=15)
            log.i(f'[TEST_DEBUG] Agent-reachable screenshot: {agent_screenshot_resp.status_code}')
            
            if agent_screenshot_resp.status_code != 200:
                log.e(f'[TEST_DEBUG] Agent screenshot URL FAILED: {agent_screenshot_resp.text[:500]}')
            else:
                log.i(f'[TEST_DEBUG] Agent screenshot URL SUCCESS: {len(agent_screenshot_resp.content)} bytes')
                
        except Exception as agent_test_exc:
            log.e(f'[TEST_DEBUG] Agent URL test failed: {agent_test_exc}')

        # 6) Run agent task
        task_description = 'RealSense Viewer is already opened, start stereo module and verify if Stereo Module depth stream looks healthy or not then return the stream health status as final answer'
        agent_client.custom_task = agent_client.build_task_with_os(
            task_description, 
            gui_url, 
            gui_server
        )
        
        result_body, result_code = agent_client.start_run()
        test.check(result_code in (HttpStatusCode.OK, HttpStatusCode.ACCEPTED))
        
        # 7) Parse and validate result
        result_data = agent_client.validate_and_log_result(result_body, log.i)
        
        test.check(result_data['success'])
        if not result_data['success']:
            log.e(f"Agent task failed - ok: {result_data['ok']}, passed: {result_data['passed']}, exit_code: {result_data['exit_code']}")

    finally:
        # Clean up all components
        viewer_mgr.cleanup()
        gui_server.cleanup()

test.print_results_and_exit()
