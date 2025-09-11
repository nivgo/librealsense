# License: Apache 2.0. See LICENSE file in root directory.
# Stereo Viewer Health Test invoking external agent automation.

import os, json, subprocess, time
from rspy import test, log
import urllib.request
import urllib.error

# Environment-controlled settings
SERVER_HOST = os.environ.get('AGENT_SERVER_HOST', '127.0.0.1')
SERVER_PORT = int(os.environ.get('AGENT_SERVER_PORT', '8099'))
TIMEOUT_SEC = float(os.environ.get('AGENT_SERVER_TIMEOUT_SEC', '900'))
POLL_INTERVAL = float(os.environ.get('AGENT_SERVER_POLL_INTERVAL_SEC', '2'))
FORCE = os.environ.get('AGENT_SERVER_FORCE', '0') in ('1','true','yes')
CUSTOM_TASK = os.environ.get('AGENT_SERVER_TASK')  # optional override, please do not do without consulting Niv

BASE_URL = f'http://{SERVER_HOST}:{SERVER_PORT}'

RUN_RESULT = None


def _http_get(url: str):
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read().decode('utf-8'), resp.getcode()
    except urllib.error.HTTPError as e:
        return e.read().decode('utf-8', 'replace'), e.code
    except Exception as e:
        return str(e), None


def _http_post(url: str, data: bytes | None = None, headers: dict | None = None, timeout: float = 30):
    req = urllib.request.Request(url, data=data, method='POST', headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8'), resp.getcode()
    except urllib.error.HTTPError as e:
        return e.read().decode('utf-8', 'replace'), e.code
    except Exception as e:
        return str(e), None


def _json_load(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None

with test.closure("Stereo depth health scenario via agent server"):
    # 1. Health check
    body, code = _http_get(BASE_URL + '/healthz')
    test.check(code == 200)
    if code != 200:
        log.e('Health check failed:', code, body)
        test.fail()
    else:
        log.d('Healthz:', body)

    # 2. Start blocking run
    query = f'wait=1&timeout_sec={int(TIMEOUT_SEC)}&poll_interval_sec={POLL_INTERVAL}'
    if FORCE:
        query += '&force=1'
    run_url = BASE_URL + '/run?' + query

    payload = None
    headers = {}
    if CUSTOM_TASK:
        payload = json.dumps({'task': CUSTOM_TASK, 'wait': True, 'timeout_sec': TIMEOUT_SEC, 'poll_interval_sec': POLL_INTERVAL}).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        run_url = BASE_URL + '/run'  # no query if sending JSON body

    log.i('Starting run:', run_url, 'payload' if payload else '')
    # Increase client timeout to allow full blocking duration (server may run long)
    post_timeout = TIMEOUT_SEC + 60  # grace period
    body, code = _http_post(run_url, data=payload, headers=headers, timeout=post_timeout)
    if code is None and body == 'timed out':
        log.e('Blocking POST client-side timeout; falling back to async polling mode')
        # Retry without wait=1
        query_async = f'timeout_sec={int(TIMEOUT_SEC)}&poll_interval_sec={POLL_INTERVAL}'
        if FORCE:
            query_async += '&force=1'
        run_url_async = BASE_URL + '/run?' + query_async
        body, code = _http_post(run_url_async, timeout=30)
    log.d('Run response code:', code)
    log.d('Run response body len:', len(body) if isinstance(body, str) else 0)
    resp_json = _json_load(body)
    test.check(code in (200,202))
    test.check(resp_json is not None)
    if resp_json is None:
        log.e('Non JSON response:', (body or '')[:300])
        test.fail()
    else:
        log.d('Parsed JSON keys:', list(resp_json.keys()))

    # If async (mode == async) then poll /result
    mode = resp_json.get('mode')
    current_run_id = resp_json.get('run_id')
    if mode != 'blocking':
        log.i('Server returned mode', mode, '- entering polling loop')
        start = time.time()
        while time.time() - start < TIMEOUT_SEC:
            b2, c2 = _http_get(BASE_URL + '/status')
            js2 = _json_load(b2)
            if js2 and js2.get('final_answer') is not None and js2.get('running') is False and js2.get('run_id') == current_run_id:
                break
            time.sleep(POLL_INTERVAL)
        b2, c2 = _http_get(BASE_URL + '/result')
        js_final = _json_load(b2)
        if js_final and js_final.get('run_id') == current_run_id:
            resp_json = js_final

    # Validate outcome
    ok = resp_json.get('ok')
    final_answer = resp_json.get('final_answer')
    passed = resp_json.get('pass')
    exit_code = resp_json.get('exit_code')
    details = resp_json.get('details')

    log.i('Result ok=', ok, 'pass=', passed, 'exit_code=', exit_code)
    log.i('Final answer:', final_answer)
    log.i('Details:', details)

    test.check(ok is True)
    test.check(passed is True)
    test.check(exit_code == 0)
    if not (ok and passed and exit_code == 0):
        test.fail()

# Print test framework summary
from rspy import test as _t
_t.print_results_and_exit()
