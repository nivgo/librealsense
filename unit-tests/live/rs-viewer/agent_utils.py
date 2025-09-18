import os
import json
import urllib.request
import urllib.error

class AgentServerClient:
    def __init__(self, host=None, port=None, timeout=None, poll_interval=None, force=False, custom_task=None):
        self.host = host or os.environ.get('AGENT_SERVER_HOST', '127.0.0.1')
        self.port = int(port or os.environ.get('AGENT_SERVER_PORT', '8099'))
        self.timeout = float(timeout or os.environ.get('AGENT_SERVER_TIMEOUT_SEC', 300.0))
        self.poll_interval = float(poll_interval or os.environ.get('AGENT_SERVER_POLL_INTERVAL_SEC', '2'))
        self.force = force or os.environ.get('AGENT_SERVER_FORCE', '0') in ('1', 'true', 'yes')
        self.custom_task = custom_task or os.environ.get('AGENT_SERVER_TASK')
        self.base_url = f'http://{self.host}:{self.port}'

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
