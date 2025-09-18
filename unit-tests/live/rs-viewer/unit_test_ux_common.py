import os
import subprocess
import time

class ViewerProcessManager:
    def __init__(self, exe_path=None):
        self.exe_path = exe_path
        self.process = None

    @staticmethod
    def find_executable():
        # Try repo finder, PATH, and common build dirs
        import shutil
        exe = None
        try:
            from rspy import repo
            exe = repo.find_built_exe('tools/realsense-viewer', 'realsense-viewer')
        except Exception:
            pass
        if not exe:
            exe = shutil.which('realsense-viewer')
        if not exe:
            for build_dir in ['build', '../build', './build']:
                candidate = os.path.join(build_dir, 'tools', 'realsense-viewer', 'realsense-viewer')
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    exe = candidate
                    break
        return exe

    def start(self):
        if not self.exe_path:
            self.exe_path = self.find_executable()
        if not self.exe_path:
            raise RuntimeError('realsense-viewer executable not found!')
        env = os.environ.copy()
        if 'DISPLAY' not in env:
            env['DISPLAY'] = ':0'
        self.process = subprocess.Popen([self.exe_path],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        universal_newlines=True,
                                        env=env)
        time.sleep(5)
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(f'Process failed to start. stdout: {stdout}\nstderr: {stderr}')
        time.sleep(5)
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
