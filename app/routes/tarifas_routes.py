from flask import Blueprint, request, jsonify
from app.models import TarifaHabitacion, db
from sqlalchemy.exc import IntegrityError

tarifas_bp = Blueprint('tarifas_bp', __name__)

# OBTENER TODAS LAS TARIFAS
@tarifas_bp.route('/obtenerTarifas', methods=['GET'])
def obtener_tarifas():
    try:
        tarifas = TarifaHabitacion.query.order_by(TarifaHabitacion.orden).all()
        result = []
        for t in tarifas:
            result.append({
                'id': t.id,
                'nombre': t.nombre,
                'precio_mxn': float(t.precio_mxn),
                'orden': t.orden
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# CREAR TARIFA
@tarifas_bp.route('/crearTarifa', methods=['POST'])
def crear_tarifa():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        nombre = data.get('nombre')
        precio_mxn = data.get('precio_mxn')
        orden = data.get('orden', 0)

        if not nombre or precio_mxn is None:
            return jsonify({'error': 'Nombre and precio_mxn are required'}), 400

        nueva_tarifa = TarifaHabitacion(
            nombre=nombre,
            precio_mxn=precio_mxn,
            orden=orden
        )
        db.session.add(nueva_tarifa)
        db.session.commit()

        return jsonify({'message': 'Tarifa creada exitosamente', 'id': nueva_tarifa.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ACTUALIZAR TARIFA
@tarifas_bp.route('/actualizar/<int:id>', methods=['PUT'])
def actualizar_tarifa(id):
    try:
        tarifa = TarifaHabitacion.query.get(id)
        if not tarifa:
            return jsonify({'message': 'Tarifa no encontrada'}), 404

        data = request.get_json()
        if 'nombre' in data:
            tarifa.nombre = data['nombre']
        if 'precio_mxn' in data:
            tarifa.precio_mxn = data['precio_mxn']
        if 'orden' in data:
            tarifa.orden = data['orden']

        db.session.commit()
        return jsonify({'message': 'Tarifa actualizada exitosamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ELIMINAR TARIFA
@tarifas_bp.route('/eliminar/<int:id>', methods=['DELETE'])
def eliminar_tarifa(id):
    try:
        tarifa = TarifaHabitacion.query.get(id)
        if not tarifa:
            return jsonify({'message': 'Tarifa no encontrada'}), 404

        db.session.delete(tarifa)
        db.session.commit()
        return jsonify({'message': 'Tarifa eliminada exitosamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500