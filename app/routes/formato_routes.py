from flask import Blueprint, request, jsonify
from app.models import Empleado, Encargado, Usuario


# Definición del Blueprint para las rutas de obtención de datos
formato_bp = Blueprint('formato_bp', __name__)



# NUEVA RUTA PARA OBTENER TODOS LOS FORMATOS ----------------------------------------------------------
@formato_bp.route('/formatos', methods=['OPTIONS', 'GET'])
def obtener_formatos():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        formatos = Formato.query.all()
        
        if not formatos:
            return jsonify({'message': 'No hay formatos disponibles'}), 404
        
        formatos_data = []
        for formato in formatos:
            formato_data = {
                'id': formato.id,
                'nombre': formato.nombre,
                'descripcion': formato.descripcion,
                'archivo_url': formato.archivo_url,
                'fecha_subida': formato.fecha_subida.strftime('%Y-%m-%d %H:%M:%S')
            }
            formatos_data.append(formato_data)
        
        return jsonify({
            'total': len(formatos_data),
            'formatos': formatos_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------- DESCARGAR FORMATO ----------------------------------------------------------
@formato_bp.route('/formatos/download/<int:formato_id>', methods=['GET'])
def download_formato(formato_id):
    try:
        formato = Formato.query.get(formato_id)
        if not formato:
            return jsonify({'error': 'Formato no encontrado'}), 404

        carpeta_formatos = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads', 'formatos')
        filename = os.path.basename(formato.archivo_url)  # Esto evita rutas raras
        return send_from_directory(carpeta_formatos, filename, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500