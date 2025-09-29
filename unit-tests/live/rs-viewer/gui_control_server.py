#!/usr/bin/env python3
# Cross-platform GUI control server for agent/test integration (headless-safe)
from flask import Flask, request, send_file, jsonify
import argparse, os, platform, time, io, shutil, subprocess

def _has_display() -> bool:
    # Windows/macOS generally OK; Linux needs DISPLAY
    if platform.system() == "Linux":
        return bool(os.environ.get("DISPLAY"))
    return True

def _load_pyautogui():
    # Lazy import; only try when a display likely exists
    try:
        if not _has_display():
            return None
        import pyautogui  # type: ignore
        # Make pyautogui a bit faster/predictable
        try:
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0.0
        except Exception:
            pass
        return pyautogui
    except Exception:
        return None

def _screenshot_bytes():
    """Return PNG bytes of current screen; MSS fallback works headless."""
    pyauto = _load_pyautogui()
    if pyauto is not None:
        img = pyauto.screenshot()
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    # Fallback to mss (headless-friendly)
    import mss, numpy as np, cv2  # type: ignore
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = np.array(sct.grab(monitor))[:, :, :3]
        ok, enc = cv2.imencode(".png", shot)
        if not ok:
            raise RuntimeError("Failed to encode screenshot")
        return io.BytesIO(enc.tobytes())

def _wiggle_cursor_with_xdotool(x: int, y: int):
    """Best-effort cursor wiggle via xdotool to make the target obvious."""
    if platform.system() != "Linux" or not shutil.which("xdotool"):
        return
    try:
        subprocess.run(["xdotool", "mousemove", str(x), str(y)],
                       check=False, capture_output=True, timeout=1.5)
        for dx, dy in [(-12, 0), (12, 0), (0, -12), (0, 12), (0, 0)]:
            nx, ny = x + dx, y + dy
            subprocess.run(["xdotool", "mousemove", str(nx), str(ny)],
                           check=False, capture_output=True, timeout=1.0)
            time.sleep(0.06)
    except Exception:
        pass

def _manual_click(pyauto, x: int, y: int, button: str = "left", double: bool = False,
                  move_duration: float = 0.05, inter_click_delay: float = 0.15):
    """
    Perform a click using moveTo + mouseDown/mouseUp (more reliable for some UIs).
    """
    pyauto.moveTo(int(x), int(y), duration=float(move_duration))

    def _once():
        pyauto.mouseDown(button=button)
        time.sleep(0.2)  # small dwell so the target gets the press
        pyauto.mouseUp(button=button)

    if double:
        _once()
        time.sleep(float(inter_click_delay))
        _once()
    else:
        _once()

app = Flask(__name__)

@app.get("/healthz")
def healthz():
    info = {
        "ok": True,
        "platform": platform.system(),
        "os": platform.system().lower(),  # normalized OS name for agent
        "display": _has_display(),
        "pyautogui": _load_pyautogui() is not None,
        "time": int(time.time()),
    }
    return jsonify(info)

@app.get("/screenshot")
def screenshot():
    buf = _screenshot_bytes()
    return send_file(buf, mimetype='image/png')

@app.post("/action")
def action():
    data = request.json or {}
    atype = data.get("type")
    if not atype:
        return jsonify({"success": False, "error": "Missing action type"}), 400

    pyauto = _load_pyautogui()

    if atype == "click":
        if pyauto is None:
            return jsonify({"success": False, "error": "Headless: no display/pyautogui"}), 501

        try:
            x = int(data.get("x", 0)); y = int(data.get("y", 0))
        except Exception:
            return jsonify({"success": False, "error": "x/y must be integers"}), 400

        button = str(data.get("button", "left"))
        double = bool(data.get("double", False))
        visualize = bool(data.get("visualize", False))
        pre_delay_ms = int(data.get("pre_delay_ms", 0))
        move_duration = float(data.get("move_duration", 0.05))
        inter_click_delay = float(data.get("inter_click_delay", 0.15))

        # Optional tiny pre-delay (e.g., to allow a menu to settle)
        if pre_delay_ms > 0:
            time.sleep(pre_delay_ms / 1000.0)

        # Optional wiggle visualization (Linux + xdotool)
        if visualize:
            _wiggle_cursor_with_xdotool(x, y)
            # leave the cursor at target for a short moment before clicking
            time.sleep(0.15)

        try:
            _manual_click(pyauto, x, y, button=button, double=double,
                          move_duration=move_duration, inter_click_delay=inter_click_delay)
            return jsonify({
                "success": True,
                "clicked": [x, y],
                "button": button,
                "double": double,
                "method": "pyautogui_manual"
            })
        except Exception as e:
            return jsonify({"success": False, "error": f"click failed: {e}"}), 500

    if atype == "mousemove":
        if pyauto is None:
            return jsonify({"success": False, "error": "Headless: no display/pyautogui"}), 501
        try:
            x = int(data.get("x", 0)); y = int(data.get("y", 0))
            dur = float(data.get("duration", 0.05))
        except Exception:
            return jsonify({"success": False, "error": "invalid x/y/duration"}), 400
        pyauto.moveTo(x, y, duration=dur)
        return jsonify({"success": True, "moved": [x, y], "duration": dur})

    if atype == "keypress":
        if pyauto is None:
            return jsonify({"success": False, "error": "Headless: no display/pyautogui"}), 501
        key = str(data.get("key", "f11"))
        try:
            pyauto.press(key)
            return jsonify({"success": True, "action": "keypress", "key": key})
        except Exception as e:
            return jsonify({"success": False, "error": f"keypress failed: {e}"}), 500

    if atype == "fullscreen":
        if pyauto is None:
            return jsonify({"success": False, "error": "Headless: no display/pyautogui"}), 501
        
        # Enhanced fullscreen for Linux
        if platform.system() == "Linux":
            # Try multiple methods for better reliability
            success_methods = []
            
            # Method 1: Find and focus window first, then F11
            if shutil.which("xdotool"):
                window_patterns = ['RealSense Viewer', 'Intel RealSense Viewer', 'realsense']
                window_found = False
                
                for pattern in window_patterns:
                    try:
                        result = subprocess.run(['xdotool', 'search', '--name', pattern], 
                                              capture_output=True, text=True, timeout=3)
                        if result.returncode == 0 and result.stdout.strip():
                            window_ids = result.stdout.strip().split('\n')
                            for win_id in window_ids[:1]:  # Use first match
                                # Activate window
                                subprocess.run(['xdotool', 'windowactivate', win_id], 
                                             capture_output=True, timeout=2)
                                time.sleep(0.3)
                                # Send F11
                                subprocess.run(['xdotool', 'key', 'F11'], 
                                             capture_output=True, timeout=2)
                                window_found = True
                                success_methods.append(f"xdotool+F11 (pattern: {pattern})")
                                break
                    except Exception as e:
                        continue
                    if window_found:
                        break
            
            # Method 2: Fallback to wmctrl fullscreen toggle
            if not success_methods and shutil.which("wmctrl"):
                window_patterns = ['RealSense Viewer', 'Intel RealSense Viewer']
                for pattern in window_patterns:
                    try:
                        result = subprocess.run(['wmctrl', '-r', pattern, '-b', 'toggle,fullscreen'], 
                                              capture_output=True, text=True, timeout=3)
                        if result.returncode == 0:
                            success_methods.append(f"wmctrl fullscreen (pattern: {pattern})")
                            break
                    except Exception:
                        continue
            
            # Method 3: Fallback to pyautogui F11
            if not success_methods:
                try:
                    pyauto.press("f11")
                    success_methods.append("pyautogui F11")
                except Exception as e:
                    pass
            
            if success_methods:
                return jsonify({"success": True, "action": "fullscreen", "methods": success_methods})
            else:
                return jsonify({"success": False, "error": "All fullscreen methods failed. Install wmctrl/xdotool."})
        
        # Windows/default: just F11
        try:
            pyauto.press("f11")
            return jsonify({"success": True, "action": "fullscreen"})
        except Exception as e:
            return jsonify({"success": False, "error": f"fullscreen failed: {e}"}), 500

    if atype == "maximize_viewer":
        # Best-effort on Linux with wmctrl; Windows with pyautogui
        if platform.system() == "Linux":
            if shutil.which("wmctrl"):
                window_patterns = ['RealSense Viewer', 'Intel RealSense Viewer']
                success = False
                used_pattern = None
                
                for pattern in window_patterns:
                    try:
                        result = subprocess.run(['wmctrl', '-r', pattern, '-b', 'add,maximized_vert,maximized_horz'], 
                                              capture_output=True, text=True, timeout=3)
                        if result.returncode == 0:
                            success = True
                            used_pattern = pattern
                            break
                    except Exception:
                        continue
                
                if success:
                    return jsonify({"success": True, "action": "maximize_viewer", "pattern": used_pattern})
                else:
                    return jsonify({"success": False, "error": "wmctrl failed to find RealSense Viewer window"}), 404
            return jsonify({"success": False, "error": "wmctrl not installed"}), 501
        elif platform.system() == "Windows":
            pyauto = _load_pyautogui()
            if pyauto:
                try:
                    # Find RealSense Viewer window
                    windows = pyauto.getWindowsWithTitle('RealSense Viewer')
                    if not windows:
                        windows = pyauto.getWindowsWithTitle('Intel RealSense Viewer')
                    if not windows:
                        # Try to find any window with "RealSense" in the title
                        all_windows = pyauto.getAllWindows()
                        windows = [w for w in all_windows if 'realsense' in w.title.lower()]
                    
                    if windows:
                        # Use the first matching window
                        window = windows[0]
                        window.activate()
                        time.sleep(0.3)
                        window.maximize()
                        return jsonify({"success": True, "action": "maximize_viewer", "window_title": window.title})
                    else:
                        return jsonify({"success": False, "error": "RealSense Viewer window not found"}), 404
                except Exception as e:
                    return jsonify({"success": False, "error": f"maximize failed: {e}"}), 500
            else:
                return jsonify({"success": False, "error": "pyautogui not available"}), 501
        return jsonify({"success": False, "error": "maximize_viewer not implemented for this platform"}), 400

    if atype == "focus_viewer":
        if platform.system() == "Linux":
            if shutil.which("xdotool"):
                window_patterns = ['RealSense Viewer', 'Intel RealSense Viewer', 'realsense']
                success = False
                used_pattern = None
                
                for pattern in window_patterns:
                    try:
                        result = subprocess.run(['xdotool', 'search', '--name', pattern, 'windowactivate'], 
                                              capture_output=True, text=True, timeout=3)
                        if result.returncode == 0:
                            success = True
                            used_pattern = pattern
                            break
                    except Exception:
                        continue
                
                if success:
                    return jsonify({"success": True, "action": "focus_viewer", "pattern": used_pattern})
                else:
                    return jsonify({"success": False, "error": "xdotool failed to find RealSense Viewer window"}), 404
            return jsonify({"success": False, "error": "xdotool not installed"}), 501
        elif platform.system() == "Windows":
            pyauto = _load_pyautogui()
            if pyauto:
                try:
                    # Find RealSense Viewer window
                    windows = pyauto.getWindowsWithTitle('RealSense Viewer')
                    if not windows:
                        windows = pyauto.getWindowsWithTitle('Intel RealSense Viewer')
                    if not windows:
                        # Try to find any window with "RealSense" in the title
                        all_windows = pyauto.getAllWindows()
                        windows = [w for w in all_windows if 'realsense' in w.title.lower()]
                    
                    if windows:
                        # Use the first matching window
                        window = windows[0]
                        window.activate()
                        return jsonify({"success": True, "action": "focus_viewer", "window_title": window.title})
                    else:
                        return jsonify({"success": False, "error": "RealSense Viewer window not found"}), 404
                except Exception as e:
                    return jsonify({"success": False, "error": f"focus failed: {e}"}), 500
            else:
                return jsonify({"success": False, "error": "pyautogui not available"}), 501
        return jsonify({"success": False, "error": "focus_viewer not implemented for this platform"}), 400

    return jsonify({"success": False, "error": f"Unknown action: {atype}"}), 400

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001)
    args = parser.parse_args()
    app.run(host="0.0.0.0", port=args.port)
