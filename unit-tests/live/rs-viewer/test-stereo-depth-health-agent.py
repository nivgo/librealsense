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
        test.check(gui_server.start())

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
