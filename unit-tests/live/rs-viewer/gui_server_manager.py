import os
import subprocess
import time
import socket
import platform
import signal
import sys
import requests
from test_constants import TestDefaults, TestTiming, WindowSetupMode

def setup_ci_environment():
    """Setup required environment variables for Jenkins/CI environment"""
    # Set required environment variables for GUI operations and agent communication
    os.environ['DISPLAY'] = TestDefaults.CI_DISPLAY
    os.environ['NO_PROXY'] = TestDefaults.CI_NO_PROXY_HOST
    os.environ['no_proxy'] = TestDefaults.CI_NO_PROXY_HOST
    
    print(f"[CI Setup] DISPLAY: {os.environ.get('DISPLAY', 'NOT_SET')}")
    print(f"[CI Setup] NO_PROXY: {os.environ.get('NO_PROXY', 'NOT_SET')}")
    print(f"[CI Setup] no_proxy: {os.environ.get('no_proxy', 'NOT_SET')}")

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
        # Add headers for JSON requests
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        return session
    
    def start(self, timeout=12):
        """Start GUI control server and wait for it to be ready"""
        server_cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), 'gui_control_server.py'),
            '--port', str(self.port),
        ]
        
        print(f"[GUI_MANAGER_DEBUG] Starting GUI server with command: {' '.join(server_cmd)}")
        print(f"[GUI_MANAGER_DEBUG] Working directory: {os.path.dirname(__file__)}")
        print(f"[GUI_MANAGER_DEBUG] Environment DISPLAY: {os.environ.get('DISPLAY', 'NOT_SET')}")
        
        self.process = subprocess.Popen(server_cmd, cwd=os.path.dirname(__file__))
        print(f"[GUI_MANAGER_DEBUG] GUI server process started with PID: {self.process.pid}")
        
        # Wait for server to be ready
        ready = self.wait_ready(timeout=timeout)
        print(f"[GUI_MANAGER_DEBUG] GUI server ready status: {ready}")
        return ready
    
    def wait_ready(self, timeout=12):
        """Wait for GUI control server to become ready"""
        print(f"[GUI_MANAGER_DEBUG] Waiting for GUI server to be ready (timeout: {timeout}s)")
        t0 = time.time()
        attempt = 0
        
        while time.time() - t0 < timeout:
            attempt += 1
            try:
                health_url = f'http://127.0.0.1:{self.port}/healthz'
                print(f"[GUI_MANAGER_DEBUG] Health check attempt {attempt} to {health_url}")
                r = self.session.get(health_url, timeout=2)
                print(f"[GUI_MANAGER_DEBUG] Health check response: {r.status_code}")
                
                if 200 <= r.status_code < 300:
                    print(f"[GUI_MANAGER_DEBUG] GUI server ready after {time.time() - t0:.1f}s")
                    return True
            except Exception as e:
                print(f"[GUI_MANAGER_DEBUG] Health check attempt {attempt} failed: {e}")
            time.sleep(0.2)
            
        print(f"[GUI_MANAGER_DEBUG] GUI server NOT ready after {timeout}s timeout")
        return False
    
    def control_viewer(self, action, logger_func=None):
        """Control the viewer window using the GUI control server"""
        try:
            if logger_func:
                logger_func(f"Executing GUI action: {action}")
            
            # Use the same session with consistent configuration
            response = self.session.post(
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
    
    def setup_viewer_window(self, mode=WindowSetupMode.FULLSCREEN, logger_func=None):
        """Setup the viewer window with different modes based on test requirements"""
        if logger_func:
            logger_func(f'Setting up viewer window (mode: {mode})...')
        
        success_count = 0
        total_actions = 0
        
        # Always try to focus first - this is most important
        total_actions += 1
        if self.control_viewer('focus_viewer', logger_func=logger_func):
            success_count += 1
        time.sleep(TestTiming.WINDOW_FOCUS_DELAY)
        
        # Maximize only if requested
        if mode in [WindowSetupMode.STANDARD, WindowSetupMode.FULLSCREEN]:
            total_actions += 1
            if self.control_viewer('maximize_viewer', logger_func=logger_func):
                success_count += 1
            time.sleep(TestTiming.WINDOW_MAXIMIZE_DELAY)
        
        # Fullscreen only for agent tests that need maximum screen real estate
        if mode == WindowSetupMode.FULLSCREEN:
            total_actions += 1
            if self.control_viewer('fullscreen', logger_func=logger_func):
                success_count += 1
        
        if logger_func:
            logger_func(f'Viewer window setup completed ({success_count}/{total_actions} actions succeeded)')
        
        return success_count > 0  # Return True if at least focus worked

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
