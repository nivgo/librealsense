# Cross-platform GUI control server for agent/test integration
from flask import Flask, request, send_file, jsonify
import pyautogui
import os
import platform
import time

app = Flask(__name__)

@app.route('/screenshot', methods=['GET'])
def screenshot():
    img = pyautogui.screenshot()
    if platform.system() == 'Windows':
        path = os.path.join(os.environ.get('TEMP', 'C:\Temp'), f'screenshot_{int(time.time())}.png')
    else:
        path = f'/tmp/screenshot_{int(time.time())}.png'
    img.save(path)
    return send_file(path, mimetype='image/png')

@app.route('/action', methods=['POST'])
def action():
    data = request.json
    if not data or 'type' not in data:
        return jsonify({'success': False, 'error': 'Missing action type'}), 400

    if data['type'] == 'click':
        x = int(data.get('x', 0))
        y = int(data.get('y', 0))
        button = data.get('button', 'left')
        double = bool(data.get('double', False))
        pyautogui.moveTo(x, y)
        if double:
            pyautogui.click(x, y, clicks=2, button=button)
        else:
            pyautogui.click(x, y, button=button)
        return jsonify({'success': True, 'clicked': [x, y], 'button': button, 'double': double})

    elif data['type'] == 'fullscreen':
        # Send F11 key to toggle fullscreen (assumes viewer is focused)
        pyautogui.press('f11')
        return jsonify({'success': True, 'action': 'fullscreen'})

    return jsonify({'success': False, 'error': 'Unknown action'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
