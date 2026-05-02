import base64
import io
import os
import time
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

SESSION = None

def get_session():
    global SESSION
    if SESSION is None:
        print('[BG] Loading model...')
        from rembg import new_session
        SESSION = new_session('u2netp')  # ← SMALLER model (u2netp not u2net)
        print('[BG] Model ready ✅')
    return SESSION

@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    return jsonify({'status': 'ok', 'model': SESSION is not None, 'version': '4.0'})

@app.route('/remove-bg', methods=['POST', 'OPTIONS'])
def remove_background():
    if request.method == 'OPTIONS':
        r = make_response()
        r.headers['Access-Control-Allow-Origin'] = '*'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        r.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return r

    try:
        data = request.get_json(force=True, silent=True)
        if not data or 'image' not in data:
            return jsonify({'success': False, 'error': 'No image'}), 400

        image_bytes = base64.b64decode(data['image'])
        print(f'[BG] Processing {len(image_bytes)} bytes')

        # ── Resize input BEFORE processing to save memory ──
        img = Image.open(io.BytesIO(image_bytes))
        if img.width > 600 or img.height > 600:
            img.thumbnail((600, 600), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            image_bytes = buf.getvalue()
            print(f'[BG] Resized to {img.width}x{img.height}')

        from rembg import remove
        start = time.time()
        result_bytes = remove(image_bytes, session=get_session())
        print(f'[BG] Done in {time.time() - start:.1f}s')

        result_image = Image.open(io.BytesIO(result_bytes)).convert('RGBA')

        output = io.BytesIO()
        result_image.save(output, format='PNG')
        output.seek(0)
        result_b64 = base64.b64encode(output.read()).decode('utf-8')

        return jsonify({'success': True, 'result': result_b64, 'format': 'PNG'})

    except Exception as e:
        print(f'[BG] Error: {type(e).__name__}: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
