# License: Apache 2.0. See LICENSE file in root directory.
# Stereo Viewer Health Test invoking external agent automation.

import os
import sys
import json
import time
import subprocess
import shutil
import urllib.request
import urllib.error

from rspy import test, log, repo
from rspy.stopwatch import Stopwatch

# --- ignore runner-injected args we don't use (harmless if absent) ---
for a in ['--rslog']:
    if a in sys.argv:
        sys.argv.remove(a)

# Environment-controlled settings
SERVER_HOST = os.environ.get('AGENT_SERVER_HOST', '127.0.0.1')
SERVER_PORT = int(os.environ.get('AGENT_SERVER_PORT', '8099'))
TIMEOUT_SEC = float(os.environ.get('AGENT_SERVER_TIMEOUT_SEC', '300'))  # 5 minutes default
POLL_INTERVAL = float(os.environ.get('AGENT_SERVER_POLL_INTERVAL_SEC', '2'))
FORCE = os.environ.get('AGENT_SERVER_FORCE', '0') in ('1', 'true', 'yes')
CUSTOM_TASK = os.environ.get('AGENT_SERVER_TASK')

BASE_URL = 'http://{}:{}'.format(SERVER_HOST, SERVER_PORT)


def _http_get(url, timeout=30.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode('utf-8'), resp.getcode()
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode('utf-8', 'replace')
        except Exception:
            body = str(e)
        return body, e.code
    except Exception as e:
        return str(e), None


def _http_post(url, data=None, headers=None, timeout=30.0):
    req = urllib.request.Request(url, data=data, method='POST', headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8'), resp.getcode()
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode('utf-8', 'replace')
        except Exception:
            body = str(e)
        return body, e.code
    except Exception as e:
        return str(e), None


def _json_load(s):
    try:
        return json.loads(s)
    except Exception:
        return None


with test.closure("Stereo depth health scenario via agent server"):
    # Start realsense-viewer process
    rs_viewer = None
    
    # Try to find realsense-viewer executable
    # First try the repo's built exe finder
    try:
        rs_viewer = repo.find_built_exe('tools/realsense-viewer', 'realsense-viewer')
    except Exception:
        pass
    
    # If not found, try standard locations
    if not rs_viewer:
        rs_viewer = shutil.which('realsense-viewer')
    
    # Try common build directories
    if not rs_viewer:
        for build_dir in ['build', '../build', './build']:
            candidate = os.path.join(build_dir, 'tools', 'realsense-viewer', 'realsense-viewer')
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                rs_viewer = candidate
                break
    
    if not rs_viewer:
        log.e('realsense-viewer executable not found in build dirs or PATH!')
        log.e('Please ensure realsense-viewer is built or available in PATH')
        test.fail()
    
    log.i('Starting realsense-viewer process:', rs_viewer)
    viewer_process = None
    try:
        # Set up environment for GUI display
        env = os.environ.copy()
        if 'DISPLAY' not in env:
            env['DISPLAY'] = ':0'  # Default X11 display
        
        # Start realsense-viewer with GUI environment
        viewer_process = subprocess.Popen([rs_viewer], 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE,
                                        universal_newlines=True,
                                        env=env)
        # Give viewer more time to start up and show GUI
        time.sleep(5)
        
        if viewer_process.poll() is not None:
            # Get error output if process failed
            stdout, stderr = viewer_process.communicate()
            log.e('realsense-viewer process failed to start or exited early')
            log.e('stdout:', stdout)
            log.e('stderr:', stderr)
            test.fail()
        
        log.i('realsense-viewer started with PID:', viewer_process.pid)
        
        # Wait additional time for viewer to fully initialize before starting agent
        log.i('Waiting 10 seconds for realsense-viewer to fully initialize...')
        time.sleep(10)
        
        # 1) Health check
        body, code = _http_get(BASE_URL + '/healthz')
        test.check(code == 200)
        if code != 200:
            log.e('Health check failed:', code, body)
            test.fail()
        else:
            log.d('healthz:', body)

        # 2) Start run (blocking preferred; fallback to async polling)
        query = 'wait=1&timeout_sec={}&poll_interval_sec={}'.format(int(TIMEOUT_SEC), POLL_INTERVAL)
        if FORCE:
            query += '&force=1'
        run_url = BASE_URL + '/run?' + query

        payload = None
        headers = {}
        if CUSTOM_TASK:
            payload = json.dumps({
                'task': CUSTOM_TASK,
                'wait': True,
                'timeout_sec': TIMEOUT_SEC,
                'poll_interval_sec': POLL_INTERVAL
            }).encode('utf-8')
            headers['Content-Type'] = 'application/json'
            run_url = BASE_URL + '/run'  # JSON body, no query

        log.i('Starting run:', run_url, '(with payload)' if payload else '')
        post_timeout = float(TIMEOUT_SEC) + 60.0  # grace period beyond server timeout
        body, code = _http_post(run_url, data=payload, headers=headers, timeout=post_timeout)

        # Client POST timeout: retry in async mode
        if code is None and isinstance(body, str) and 'timed out' in body.lower():
            log.e('Blocking POST client-side timeout; falling back to async polling mode')
            query_async = 'timeout_sec={}&poll_interval_sec={}'.format(int(TIMEOUT_SEC), POLL_INTERVAL)
            if FORCE:
                query_async += '&force=1'
            run_url_async = BASE_URL + '/run?' + query_async
            body, code = _http_post(run_url_async, timeout=30.0)

        log.d('Run response code:', code)
        log.d('Run response body len:', len(body) if isinstance(body, str) else 0)

        resp_json = _json_load(body)
        test.check(code in (200, 202))
        test.check(resp_json is not None)
        if resp_json is None:
            log.e('Non-JSON response:', (body or '')[:300])
            test.fail()
        else:
            log.d('Parsed JSON keys:', list(resp_json.keys()))

        # 3) If async, poll for completion
        if resp_json:
            mode = resp_json.get('mode')
            current_run_id = resp_json.get('run_id')
            if mode != 'blocking':
                log.i('Server returned mode', mode, '- entering polling loop')
                start = time.time()
                sleep_dt = POLL_INTERVAL if POLL_INTERVAL > 0 else 0.5
                while time.time() - start < TIMEOUT_SEC:
                    b2, c2 = _http_get(BASE_URL + '/status')
                    js2 = _json_load(b2)
                    if js2 \
                       and js2.get('run_id') == current_run_id \
                       and js2.get('running') is False \
                       and js2.get('final_answer') is not None:
                        break
                    time.sleep(sleep_dt)

                b2, c2 = _http_get(BASE_URL + '/result')
                js_final = _json_load(b2)
                if js_final and js_final.get('run_id') == current_run_id:
                    resp_json = js_final

        # 4) Validate outcome
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
        test.check(exit_code == 0)
        if not (ok and passed and exit_code == 0):
            test.fail()

    finally:
        # Clean up realsense-viewer process
        if viewer_process:
            log.i('Terminating realsense-viewer process')
            try:
                viewer_process.terminate()
                # Give it a chance to terminate gracefully
                viewer_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log.w('realsense-viewer did not terminate gracefully, killing it')
                viewer_process.kill()
                viewer_process.wait()
            except Exception as e:
                log.e('Error terminating realsense-viewer:', str(e))
            log.i('realsense-viewer process cleaned up')

test.print_results_and_exit()
