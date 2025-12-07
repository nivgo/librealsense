import os
import subprocess
import time
import platform
from test_constants import TestTiming

class ViewerProcessManager:
    def __init__(self, exe_path=None):
        self.exe_path = exe_path
        self.process = None

    def start(self):
        if not self.exe_path:
            raise RuntimeError('realsense-viewer executable path not provided!')
            
        env = os.environ.copy()
        # DISPLAY is only needed on Linux
        if platform.system() == 'Linux' and 'DISPLAY' not in env:
            env['DISPLAY'] = ':0'
            
        self.process = subprocess.Popen([self.exe_path],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        universal_newlines=True,
                                        env=env)
        
        # Wait longer for the viewer to start, especially on Windows
        if platform.system() == 'Windows':
            time.sleep(TestTiming.VIEWER_STARTUP_DELAY_WINDOWS)  # Extra time for Windows GUI apps
        else:
            time.sleep(TestTiming.VIEWER_STARTUP_DELAY)
            
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(f'Process failed to start. stdout: {stdout}\nstderr: {stderr}')
        
        # Additional wait to ensure the window is fully rendered
        time.sleep(TestTiming.VIEWER_ADDITIONAL_WAIT)
        return self.process

    def cleanup(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except Exception:
                pass
            self.process = None
