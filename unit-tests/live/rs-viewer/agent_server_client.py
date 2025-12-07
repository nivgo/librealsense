import os
import json
import urllib.request
import urllib.error
import time
import socket
import requests
from urllib.parse import urlparse
from test_constants import TestDefaults

class AgentServerClient:
    def __init__(self, host=None, port=None, timeout=None, poll_interval=None, force=False, custom_task=None, bypass_proxy=True):
        self.host = host or os.environ.get('AGENT_SERVER_HOST', TestDefaults.AGENT_SERVER_HOST)
        self.port = int(port or os.environ.get('AGENT_SERVER_PORT', TestDefaults.AGENT_SERVER_PORT))
        self.timeout = float(timeout or os.environ.get('AGENT_SERVER_TIMEOUT_SEC', TestDefaults.DEFAULT_TIMEOUT))
        self.poll_interval = float(poll_interval or os.environ.get('AGENT_SERVER_POLL_INTERVAL_SEC', TestDefaults.POLL_INTERVAL))
        self.force = force or os.environ.get('AGENT_SERVER_FORCE', '0') in ('1', 'true', 'yes')
        self.custom_task = custom_task or os.environ.get('AGENT_SERVER_TASK')
        self.bypass_proxy = bypass_proxy and os.environ.get('AGENT_SERVER_BYPASS_PROXY', '1') in ('1', 'true', 'yes')
        self.base_url = f'http://{self.host}:{self.port}'
        
        # Automatically add agent host to no_proxy if bypass_proxy is enabled
        if self.bypass_proxy:
            self._setup_proxy_bypass()

    def _setup_proxy_bypass(self):
        """Configure no_proxy environment variables to bypass proxy for agent server."""
        # Both uppercase and lowercase versions for cross-platform compatibility
        for env_var in ['NO_PROXY', 'no_proxy']:
            current_no_proxy = os.environ.get(env_var, '')
            
            # Parse existing no_proxy entries
            if current_no_proxy:
                no_proxy_list = [host.strip() for host in current_no_proxy.split(',')]
            else:
                no_proxy_list = []
            
            # Add agent host if not already present
            if self.host not in no_proxy_list:
                no_proxy_list.append(self.host)
                
            # Update environment variable
            os.environ[env_var] = ','.join(no_proxy_list)

    def _http_get(self, url, timeout=30.0):
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

    def _http_post(self, url, data=None, headers=None, timeout=30.0):
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

    def build_task_with_os(self, description, gui_control_url, gui_server_manager):
        """Build agent task with OS detection from GUI server"""
        gui_os = gui_server_manager.get_os_info()
        return {
            'description': description,
            'gui_control_url': gui_control_url,
            'os': gui_os,
        }

    def health_check(self):
        return self._http_get(self.base_url + '/healthz')

    def start_run(self):
        query = f'wait=1&timeout_sec={int(self.timeout)}&poll_interval_sec={self.poll_interval}'
        if self.force:
            query += '&force=1'
        run_url = self.base_url + '/run?' + query
        payload = None
        headers = {}
        if self.custom_task:
            payload = json.dumps({
                'task': self.custom_task,
                'wait': True,
                'timeout_sec': self.timeout,
                'poll_interval_sec': self.poll_interval
            }).encode('utf-8')
            headers['Content-Type'] = 'application/json'
            run_url = self.base_url + '/run'
        post_timeout = float(self.timeout) + 60.0
        return self._http_post(run_url, data=payload, headers=headers, timeout=post_timeout)

    def poll_status(self):
        return self._http_get(self.base_url + '/status')

    def get_result(self):
        return self._http_get(self.base_url + '/result')

    @staticmethod
    def json_load(s):
        try:
            return json.loads(s)
        except Exception:
            return None
    
    def validate_and_log_result(self, result_body, logger_func=None):
        """Parse agent result and return validation status with detailed logging."""
        if logger_func is None:
            logger_func = print  # Default fallback
            
        resp_json = self.json_load(result_body) or {}
        
        # Extract result fields
        ok = resp_json.get('ok')
        passed = resp_json.get('pass')
        exit_code = resp_json.get('exit_code')
        final_answer = resp_json.get('final_answer')
        details = resp_json.get('details')
        
        # Log all result details
        logger_func(f'Agent result - ok: {ok}, pass: {passed}, exit_code: {exit_code}')
        logger_func(f'Final answer: {final_answer}')
        logger_func(f'Details: {details}')
        
        # Validate success criteria
        success = ok is True and passed is True and exit_code in (0, None)
        
        return {
            'success': success,
            'ok': ok,
            'passed': passed,
            'exit_code': exit_code,
            'final_answer': final_answer,
            'details': details,
            'raw_response': resp_json
        }


class HttpClient:
    """HTTP client with session management for agent communication."""
    
    def __init__(self):
        # Use a session that ignores proxies for direct IP calls
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.proxies = {"http": None, "https": None}
    
    def wait_http_ready(self, url, timeout=12):
        """Wait for HTTP service to be ready."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                r = self.session.get(url, timeout=2)
                if 200 <= r.status_code < 300:
                    return True, r
            except Exception:
                pass
            time.sleep(0.2)
        return False, None
    
    def post_json(self, url, payload, timeout=12):
        """POST JSON payload and return response."""
        r = self.session.post(url, json=payload, timeout=timeout)
        try:
            return r.json(), r.status_code
        except Exception:
            return r.text, r.status_code
    
    def get_json(self, url, timeout=12):
        """GET request and return JSON response."""
        r = self.session.get(url, timeout=timeout)
        try:
            return r.json(), r.status_code
        except Exception:
            return r.text, r.status_code


def get_local_ip_for(dest_host: str) -> str:
    """Outward-facing local IP that can reach dest_host (no packets sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((dest_host, 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


class AgentTestManager:
    """Manager for running agent-based tests."""
    
    def __init__(self, agent_url=None, poll_interval=None, timeout_sec=None):
        self.agent_url = agent_url or os.environ.get("AGENT_SERVER_URL", "http://143.185.122.14:8099")
        self.poll_interval = float(poll_interval or os.environ.get("AGENT_POLL_INTERVAL", "0.5"))
        self.timeout_sec = int(timeout_sec or os.environ.get("AGENT_TIMEOUT", "120"))
        self.http_client = HttpClient()
        
    def check_health(self):
        """Check if agent server is healthy."""
        try:
            r = self.http_client.session.get(f'{self.agent_url}/healthz', timeout=5)
            body = r.text
            code = r.status_code
        except Exception as e:
            body, code = str(e), None
        return code == 200, body, code
        
    def build_gui_url(self, gui_port):
        """Build GUI URL reachable from the agent host."""
        agent_host = urlparse(self.agent_url).hostname or "127.0.0.1"
        gui_host_ip = get_local_ip_for(agent_host)
        return f'http://{gui_host_ip}:{gui_port}'
        
    def run_task(self, task_description, gui_url, gui_os, start_time):
        """Run a task on the agent server."""
        task = {
            'description': task_description,
            'gui_control_url': gui_url,
            'os': gui_os,
        }
        
        resp_json, code = self.http_client.post_json(f'{self.agent_url}/run', task, timeout=12)
        if not (code in (200, 202) and isinstance(resp_json, dict)):
            return None, f'Non-JSON response from /run: {str(resp_json)[:300]}'
            
        run_id = resp_json.get('run_id')
        mode = resp_json.get('mode', 'async')
        
        if not run_id:
            return None, 'No run_id returned from /run'
            
        # Poll if async
        if mode != 'blocking':
            while time.time() - start_time < self.timeout_sec:
                try:
                    s = self.http_client.session.get(f'{self.agent_url}/status', timeout=5)
                    js = s.json()
                except Exception:
                    js = None
                    
                if js and js.get('run_id') == run_id and js.get('running') is False and js.get('final_answer') is not None:
                    break
                time.sleep(self.poll_interval)
                
            # Fetch final result
            try:
                r = self.http_client.session.get(f'{self.agent_url}/result', timeout=10)
                resp_json = r.json() if r.headers.get('content-type','').startswith('application/json') else {}
            except Exception as e:
                return None, f'Failed to fetch final result: {e}'
        
        return resp_json, None
        
    def validate_result(self, resp_json):
        """Validate agent test result."""
        if not isinstance(resp_json, dict):
            return False, "Response is not a dictionary"
            
        ok = resp_json.get('ok')
        passed = resp_json.get('pass')  
        exit_code = resp_json.get('exit_code')
        final_ans = resp_json.get('final_answer')
        details = resp_json.get('details')
        
        success = ok is True and passed is True and exit_code in (0, None)
        
        return success, {
            'ok': ok,
            'passed': passed, 
            'exit_code': exit_code,
            'final_answer': final_ans,
            'details': details
        }
