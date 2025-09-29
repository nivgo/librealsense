import os
import subprocess
import time
import socket
import platform
import signal
import sys
import requests
from test_constants import TestDefaults

class GuiServerManager:
    """Manages the GUI control server lifecycle for rs-viewer tests"""
    
    def __init__(self, port=None):
        self.port = int(port or os.environ.get('GUI_PORT', TestDefaults.GUI_SERVER_PORT))
        self.process = None
        self.session = self._create_session()
        
    def _create_session(self):
        """Create requests session with no proxy for direct IP calls"""
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        return session
    
    def start(self, timeout=12):
        """Start GUI control server and wait for it to be ready"""
        server_cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), 'gui_control_server.py'),
            '--port', str(self.port),
        ]
        self.process = subprocess.Popen(server_cmd, cwd=os.path.dirname(__file__))
        
        # Wait for server to be ready
        return self.wait_ready(timeout=timeout)
    
    def wait_ready(self, timeout=12):
        """Wait for GUI control server to become ready"""
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                r = self.session.get(f'http://127.0.0.1:{self.port}/healthz', timeout=2)
                if 200 <= r.status_code < 300:
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        return False
    
    def control_viewer(self, action, logger_func=None):
        """Control the viewer window using the GUI control server"""
        try:
            if logger_func:
                logger_func(f"Executing GUI action: {action}")
            
            response = requests.post(
                f'http://localhost:{self.port}/action',
                json={'type': action},
                timeout=10
            )
            
            if response.status_code == 200:
                resp_data = response.json()
                if resp_data.get('success'):
                    if logger_func:
                        logger_func(f"GUI action '{action}' response: {resp_data}")
                    return True
                else:
                    if logger_func:
                        error_msg = resp_data.get('error', 'Unknown error')
                        logger_func(f"GUI action '{action}' failed: {error_msg}")
                    return False
            else:
                if logger_func:
                    logger_func(f"GUI action '{action}' failed with status {response.status_code}")
                return False
                
        except Exception as e:
            if logger_func:
                logger_func(f"Error executing GUI action '{action}': {str(e)}")
            return False
    
    def get_gui_url_for_host(self, dest_host):
        """Get GUI URL reachable from dest_host"""
        local_ip = self._get_local_ip_for(dest_host)
        return f'http://{local_ip}:{self.port}'
    
    def get_os_info(self):
        """Get OS information from GUI server"""
        try:
            response = self.session.get(f'http://127.0.0.1:{self.port}/healthz', timeout=3)
            if response.status_code == 200:
                health_data = response.json()
                return health_data.get('os', platform.system().lower())
        except Exception:
            pass
        return platform.system().lower()

    def _get_local_ip_for(self, dest_host):
        """Get outward-facing local IP that can reach dest_host"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((dest_host, 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip
    
    def cleanup(self):
        """Clean up GUI server process"""
        if self.process and self.process.poll() is None:
            try:
                if platform.system() == 'Windows':
                    self.process.terminate()
                else:
                    os.kill(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=2)
            except Exception:
                try:
                    if platform.system() == 'Windows':
                        self.process.kill()
                    else:
                        os.kill(self.process.pid, signal.SIGKILL)
                except Exception:
                    pass
        self.process = None
