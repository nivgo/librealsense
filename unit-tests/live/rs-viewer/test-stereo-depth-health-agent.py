# License: Apache 2.0. See LICENSE file in root directory.
# Stereo Viewer Health Test invoking external agent automation.

from rspy import test, log
from agent_utils import AgentServerClient
from unit_test_ux_common import ViewerProcessManager

with test.closure("Stereo depth health scenario via agent server"):
    viewer_mgr = ViewerProcessManager()
    agent = AgentServerClient()
    viewer_process = None
    try:
        # Start realsense-viewer process
        try:
            viewer_process = viewer_mgr.start()
            log.i('realsense-viewer started with PID:', viewer_process.pid)
        except Exception as e:
            log.e(str(e))
            test.fail()

        # Health check
        body, code = agent.health_check()
        test.check(code == 200)
        if code != 200:
            log.e('Health check failed:', code, body)
            test.fail()
        else:
            log.d('healthz:', body)

        # Start run
        body, code = agent.start_run()
        resp_json = agent.json_load(body)
        test.check(code in (200, 202))
        test.check(resp_json is not None)
        if resp_json is None:
            log.e('Non-JSON response:', (body or '')[:300])
            test.fail()
        else:
            log.d('Parsed JSON keys:', list(resp_json.keys()))

        # Poll for completion if async
        if resp_json:
            mode = resp_json.get('mode')
            current_run_id = resp_json.get('run_id')
            if mode != 'blocking':
                log.i('Server returned mode', mode, '- entering polling loop')
                import time
                start = time.time()
                sleep_dt = agent.poll_interval if agent.poll_interval > 0 else 0.5
                while time.time() - start < agent.timeout:
                    b2, c2 = agent.poll_status()
                    js2 = agent.json_load(b2)
                    if js2 \
                       and js2.get('run_id') == current_run_id \
                       and js2.get('running') is False \
                       and js2.get('final_answer') is not None:
                        break
                    time.sleep(sleep_dt)
                b2, c2 = agent.get_result()
                js_final = agent.json_load(b2)
                if js_final and js_final.get('run_id') == current_run_id:
                    resp_json = js_final

        # Validate outcome
        ok = resp_json.get('ok') if resp_json else None
        passed = resp_json.get('pass') if resp_json else None
        exit_code = resp_json.get('exit_code') if resp_json else None
        final_answer = resp_json.get('final_answer') if resp_json else None
        details = resp_json.get('details') if resp_json else None

        log.i('Result ok=', ok, 'pass=', passed, 'exit_code=', exit_code)
        log.i('Final answer:', final_answer)
        log.i('Details:', details)

        test.check(ok is True)
        test.check(passed is True)
        test.check(exit_code in (0, None))
        if not (ok and passed and (exit_code in (0, None))):
            test.fail()

    finally:
        viewer_mgr.cleanup()

test.print_results_and_exit()
