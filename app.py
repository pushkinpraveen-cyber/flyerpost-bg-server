import base64
import io
import os
import time
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from rembg import remove, new_session
from PIL import Image

app = Flask(__name__)

CORS(app,
     resources={r"/*": {"origins": "*"}},
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"],
     supports_credentials=False)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

# ── Lazy load — loads ONLY when first request arrives ──
SESSION = None

def get_session():
    global SESSION
    if SESSION is None:
        print('[BG] Lazy loading u2net model...')
        SESSION = new_session('u2net')
        print('[BG] Model ready ✅')
    return SESSION


@app.route('/health', methods=['GET', 'OPTIONS'])
def health():
    return jsonify({
        'status': 'ok',
        'model': SESSION is not None,
        'service': 'FlyerPost BG Removal',
        'version': '3.0'
    })


@app.route('/remove-bg', methods=['POST', 'OPTIONS'])
def remove_background():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.status_code = 200
        return response

    try:
        data = request.get_json(force=True, silent=True)
        if not data or 'image' not in data or not data['image']:
            return jsonify({'success': False, 'error': 'No image'}), 400

        try:
            image_bytes = base64.b64decode(data['image'])
        except Exception:
            return jsonify({'success': False, 'error': 'Invalid base64'}), 400

        print(f'[BG] Processing {len(image_bytes)} bytes...')
        start = time.time()

        result_bytes = remove(image_bytes, session=get_session())

        print(f'[BG] Done in {time.time() - start:.1f}s')

        result_image = Image.open(io.BytesIO(result_bytes)).convert('RGBA')

        max_size = 1200
        if result_image.width > max_size or result_image.height > max_size:
            result_image.thumbnail((max_size, max_size), Image.LANCZOS)

        output = io.BytesIO()
        result_image.save(output, format='PNG')
        output.seek(0)
        result_b64 = base64.b64encode(output.read()).decode('utf-8')

        return jsonify({
            'success': True,
            'result': result_b64,
            'format': 'PNG',
            'provider': 'render_rembg'
        })

    except Exception as e:
        print(f'[BG] Error: {type(e).__name__}: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

# NO app.run() here — gunicorn handles everything
