# ============================================================
# FlyerPost Background Removal Server
# rembg = FREE, open source, no API key needed
# Fixed: explicit CORS preflight handling for Flutter Web
# ============================================================

import base64
import io
import os
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from rembg import remove, new_session
from PIL import Image

app = Flask(__name__)

# ── Explicit CORS for Flutter Web ─────────────────────────
# Flutter Web sends OPTIONS preflight before POST
# Without this, browser blocks all requests
CORS(app,
     resources={r"/*": {"origins": "*"}},
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"],
     supports_credentials=False)

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to EVERY response including errors"""
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

# ── Pre-load model once at startup ────────────────────────
print('[BG] Loading rembg u2net model...')
SESSION = None
try:
    SESSION = new_session('u2net')
    print('[BG] Model loaded OK ✅')
except Exception as e:
    print(f'[BG] Model load warning (will retry on first request): {e}')


@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    """Health check — test this URL in browser first"""
    return jsonify({
        'status':  'ok',
        'model':   SESSION is not None,
        'service': 'FlyerPost BG Removal',
        'version': '2.0'
    })


@app.route('/remove-bg', methods=['POST', 'OPTIONS'])
def remove_background():
    # ── Handle browser preflight check ────────────────────
    # Browser sends OPTIONS before every POST
    # We must respond 200 or browser blocks the real request
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin']  = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.status_code = 200
        return response

    # ── Handle actual POST ─────────────────────────────────
    try:
        data = request.get_json(force=True, silent=True)

        if not data:
            return jsonify({'success': False, 'error': 'No JSON body'}), 400

        if 'image' not in data:
            return jsonify({'success': False, 'error': 'No image field'}), 400

        image_b64 = data['image']
        if not image_b64:
            return jsonify({'success': False, 'error': 'Empty image'}), 400

        # Decode base64 image
        try:
            image_bytes = base64.b64decode(image_b64)
        except Exception:
            return jsonify({'success': False, 'error': 'Invalid base64'}), 400

        print(f'[BG] Processing image: {len(image_bytes)} bytes')

        # Remove background
        global SESSION
        if SESSION is None:
            print('[BG] Session not loaded, trying again...')
            SESSION = new_session('u2net')

        result_bytes = remove(image_bytes, session=SESSION)

        # Convert to PNG (keeps transparency)
        result_image = Image.open(io.BytesIO(result_bytes)).convert('RGBA')

        # Resize if too large
        max_size = 1200
        if result_image.width > max_size or result_image.height > max_size:
            result_image.thumbnail((max_size, max_size), Image.LANCZOS)
            print(f'[BG] Resized to {result_image.width}x{result_image.height}')

        # Encode result to base64
        output = io.BytesIO()
        result_image.save(output, format='PNG')
        output.seek(0)
        result_b64 = base64.b64encode(output.read()).decode('utf-8')

        print(f'[BG] Done! Result: {len(result_b64)} chars base64')

        return jsonify({
            'success':  True,
            'result':   result_b64,
            'format':   'PNG',
            'provider': 'render_rembg'
        })

    except Exception as e:
        print(f'[BG] Error: {type(e).__name__}: {e}')
        return jsonify({
            'success': False,
            'error':   str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f'[BG] Starting on port {port}')
    app.run(host='0.0.0.0', port=port, debug=False)
