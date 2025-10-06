#!/usr/bin/env python3
# Cross-platform GUI control server for agent/test integration (headless-safe)
from flask import Flask, request, send_file, jsonify
import argparse, os, platform, time, io, shutil, subprocess, sys

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
    print(f"[GUI_SERVER_DEBUG] _screenshot_bytes called")
    
    pyauto = _load_pyautogui()
    print(f"[GUI_SERVER_DEBUG] PyAutoGUI loaded: {pyauto is not None}")
    
    if pyauto is not None:
        try:
            print(f"[GUI_SERVER_DEBUG] Attempting PyAutoGUI screenshot...")
            img = pyauto.screenshot()
            print(f"[GUI_SERVER_DEBUG] PyAutoGUI screenshot successful: {img.size}")
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            print(f"[GUI_SERVER_DEBUG] PyAutoGUI buffer created: {len(buf.getvalue())} bytes")
            return buf
        except Exception as e:
            print(f"[GUI_SERVER_DEBUG] PyAutoGUI screenshot failed: {e}")
            import traceback
            traceback.print_exc()

    # Fallback to mss (headless-friendly)
    print(f"[GUI_SERVER_DEBUG] Using MSS fallback...")
    try:
        import mss, numpy as np, cv2  # type: ignore
        print(f"[GUI_SERVER_DEBUG] MSS libraries imported successfully")
        
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            print(f"[GUI_SERVER_DEBUG] Monitor info: {monitor}")
            shot = np.array(sct.grab(monitor))[:, :, :3]
            print(f"[GUI_SERVER_DEBUG] MSS screenshot captured: {shot.shape}")
            ok, enc = cv2.imencode(".png", shot)
            if not ok:
                print(f"[GUI_SERVER_DEBUG] cv2.imencode failed!")
                raise RuntimeError("Failed to encode screenshot")
            print(f"[GUI_SERVER_DEBUG] MSS screenshot encoded: {len(enc.tobytes())} bytes")
            return io.BytesIO(enc.tobytes())
    except Exception as e:
        print(f"[GUI_SERVER_DEBUG] MSS fallback failed: {e}")
        import traceback
        traceback.print_exc()
        raise

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

# Add CORS support for cross-origin requests
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/action', methods=['OPTIONS'])
def action_options():
    """Handle preflight OPTIONS requests"""
    return '', 200

@app.get("/test")
def test_endpoint():
    """Simple test endpoint"""
    return jsonify({"test": "ok", "platform": platform.system()})

@app.post("/test")
def test_post():
    """Test POST endpoint"""
    data = request.get_json()
    return jsonify({"received": data, "method": "POST"})

@app.get("/healthz")
def healthz():
    info = {
        "ok": True,
        "platform": platform.system(),
        "os": platform.system().lower(),  # normalized OS name for agent
        "display": _has_display(),
        "pyautogui": _load_pyautogui() is not None,
        "time": int(time.time()),
        "display_env": os.environ.get('DISPLAY', 'NOT_SET'),
    }
    
    # Check for available tools
    if platform.system() == "Linux":
        info["xdotool_available"] = bool(shutil.which("xdotool"))
        info["wmctrl_available"] = bool(shutil.which("wmctrl"))
    
    return jsonify(info)

@app.get("/screenshot")
def screenshot():
    try:
        print(f"[GUI_SERVER_DEBUG] Screenshot endpoint called")
        print(f"[GUI_SERVER_DEBUG] Request headers: {dict(request.headers)}")
        print(f"[GUI_SERVER_DEBUG] Client IP: {request.remote_addr}")
        
        buf = _screenshot_bytes()
        
        if buf is None:
            print(f"[GUI_SERVER_DEBUG] _screenshot_bytes returned None!")
            return jsonify({"error": "Screenshot capture failed"}), 500
            
        content_length = len(buf.getvalue())
        buf.seek(0)  # Reset buffer position
        print(f"[GUI_SERVER_DEBUG] Screenshot successful, returning {content_length} bytes")
        
        return send_file(buf, mimetype='image/png')
        
    except Exception as e:
        print(f"[GUI_SERVER_DEBUG] Screenshot endpoint exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Screenshot failed: {str(e)}"}), 500

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
                return jsonify({"success": False, "error": "All fullscreen methods failed. Install wmctrl/xdotool."}), 200  # Changed from error status
        
        # Windows/default: just F11
        try:
            pyauto.press("f11")
            return jsonify({"success": True, "action": "fullscreen"})
        except Exception as e:
            return jsonify({"success": False, "error": f"fullscreen failed: {e}"}), 200  # Changed from 500

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
                    return jsonify({"success": False, "error": "wmctrl failed to find RealSense Viewer window"}), 200  # Changed from 404
            else:
                return jsonify({"success": False, "error": "wmctrl not installed - cannot maximize on Linux"}), 200  # Changed from 501
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
                        return jsonify({"success": False, "error": "RealSense Viewer window not found"}), 200  # Changed from 404
                except Exception as e:
                    return jsonify({"success": False, "error": f"maximize failed: {e}"}), 200  # Changed from 500
            else:
                return jsonify({"success": False, "error": "pyautogui not available"}), 200  # Changed from 501
        else:
            return jsonify({"success": False, "error": "maximize_viewer not implemented for this platform"}), 200  # Changed from 400

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
                    return jsonify({"success": False, "error": "xdotool failed to find RealSense Viewer window"}), 200  # Changed from 404
            else:
                return jsonify({"success": False, "error": "xdotool not installed - cannot focus viewer on Linux"}), 200  # Changed from 501
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
                        return jsonify({"success": False, "error": "RealSense Viewer window not found"}), 200  # Changed from 404
                except Exception as e:
                    return jsonify({"success": False, "error": f"focus failed: {e}"}), 200  # Changed from 500
            else:
                return jsonify({"success": False, "error": "pyautogui not available"}), 200  # Changed from 501
        else:
            return jsonify({"success": False, "error": "focus_viewer not implemented for this platform"}), 200  # Changed from 400

    return jsonify({"success": False, "error": f"Unknown action: {atype}"}), 400

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001)
    args = parser.parse_args()
    
    print(f"[GUI_SERVER_DEBUG] Starting GUI Control Server")
    print(f"[GUI_SERVER_DEBUG] Port: {args.port}")
    print(f"[GUI_SERVER_DEBUG] Platform: {platform.system()}")
    print(f"[GUI_SERVER_DEBUG] Python: {sys.version}")
    print(f"[GUI_SERVER_DEBUG] DISPLAY: {os.environ.get('DISPLAY', 'NOT_SET')}")
    print(f"[GUI_SERVER_DEBUG] Working directory: {os.getcwd()}")
    
    # Test dependencies immediately at startup
    print(f"[GUI_SERVER_DEBUG] Testing dependencies...")
    try:
        pyauto = _load_pyautogui()
        print(f"[GUI_SERVER_DEBUG] PyAutoGUI: {'Available' if pyauto else 'Not available'}")
        
        import mss
        print(f"[GUI_SERVER_DEBUG] MSS: Available")
        
        import cv2
        print(f"[GUI_SERVER_DEBUG] OpenCV: Available")
        
        # Test screenshot at startup
        print(f"[GUI_SERVER_DEBUG] Testing screenshot at startup...")
        try:
            test_buf = _screenshot_bytes()
            if test_buf:
                print(f"[GUI_SERVER_DEBUG] Startup screenshot test: SUCCESS ({len(test_buf.getvalue())} bytes)")
            else:
                print(f"[GUI_SERVER_DEBUG] Startup screenshot test: FAILED (returned None)")
        except Exception as screenshot_test_error:
            print(f"[GUI_SERVER_DEBUG] Startup screenshot test: FAILED ({screenshot_test_error})")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"[GUI_SERVER_DEBUG] Dependency test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"[GUI_SERVER_DEBUG] Starting Flask app on 0.0.0.0:{args.port}")
    app.run(host="0.0.0.0", port=args.port)
