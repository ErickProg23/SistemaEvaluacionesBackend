from flask import Blueprint, request, jsonify
from app.models import Configuracion, db

configuracion_bp = Blueprint('configuracion_bp', __name__)

# OBTENER TODAS LAS CONFIGURACIONES
@configuracion_bp.route('/obtenerConfiguraciones', methods=['GET'])
def obtener_configuraciones():
    try:
        configs = Configuracion.query.all()
        result = []
        for c in configs:
            result.append({
                'clave': c.clave,
                'valor': c.valor
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# CREAR O ACTUALIZAR CONFIGURACION (UPSERT)
@configuracion_bp.route('/guardar', methods=['POST'])
def guardar_configuracion():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        clave = data.get('clave')
        valor = data.get('valor')

        if not clave:
            return jsonify({'error': 'Clave is required'}), 400

        config = Configuracion.query.get(clave)
        if config:
            config.valor = valor
            msg = 'Configuracion actualizada'
        else:
            config = Configuracion(clave=clave, valor=valor)
            db.session.add(config)
            msg = 'Configuracion creada'
        
        db.session.commit()
        return jsonify({'message': msg, 'clave': config.clave}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ELIMINAR CONFIGURACION
@configuracion_bp.route('/eliminar/<string:clave>', methods=['DELETE'])
def eliminar_configuracion(clave):
    try:
        config = Configuracion.query.get(clave)
        if not config:
            return jsonify({'message': 'Configuracion no encontrada'}), 404

        db.session.delete(config)
        db.session.commit()
        return jsonify({'message': 'Configuracion eliminada exitosamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500