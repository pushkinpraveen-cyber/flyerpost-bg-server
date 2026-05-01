# ============================================================
# FlyerPost Background Removal Server
# rembg = FREE, open source, no API key needed
# Hosted FREE on Render.com
# ============================================================

import base64
import io
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from rembg import remove, new_session
from PIL import Image

app = Flask(__name__)

CORS(app, origins=['*'])  # Allow all origins

print('[BG] Loading rembg model on startup...')
try:
    SESSION = new_session('u2net')
    print('[BG] Model loaded OK ✅')
except Exception as e:
    print(f'[BG] Model load warning: {e}')
    SESSION = None


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'model': SESSION is not None,
        'service': 'FlyerPost BG Removal'
    })


@app.route('/remove-bg', methods=['POST'])
def remove_background():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'error': 'No image'}), 400

        # Decode image from base64
        image_bytes = base64.b64decode(data['image'])

        # Remove background
        if SESSION is not None:
            result_bytes = remove(image_bytes, session=SESSION)
        else:
            result_bytes = remove(image_bytes)

        # Convert to PNG (keeps transparency)
        result_image = Image.open(io.BytesIO(result_bytes))

        # Resize if too large
        max_size = 1200
        if result_image.width > max_size or result_image.height > max_size:
            result_image.thumbnail((max_size, max_size), Image.LANCZOS)

        # Encode result to base64
        output = io.BytesIO()
        result_image.save(output, format='PNG')
        output.seek(0)
        result_b64 = base64.b64encode(output.read()).decode('utf-8')

        return jsonify({
            'success': True,
            'result': result_b64,
            'format': 'PNG'
        })

    except Exception as e:
        print(f'[BG] Error: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)