from flask import Blueprint, send_from_directory, jsonify
import os

uploads_bp = Blueprint('uploads_bp', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@uploads_bp.route('/<path:filename>', methods=['GET'])
def serve_upload(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)
    except FileNotFoundError:
        return jsonify({'error': 'Archivo no encontrado'}), 404