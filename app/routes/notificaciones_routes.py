from flask import Blueprint, request, jsonify
from app.models import Empleado, Encargado, Usuario, Pregunta, Notificacion
from app import db
from sqlalchemy import update
from datetime import datetime, timedelta



# Definición del Blueprint para las rutas de obtención de datos
notis_bp = Blueprint('notis_bp', __name__)


#----------------------------NOTIFICACIONES------------------------------------------------------
@notis_bp.route('/notificaciones/nueva', methods=['OPTIONS', 'POST'])
def nueva_notificacion():
    # Obtener el payload de la solicitud

     # 1. Verificar el tipo de solicitud
    if request.method == 'OPTIONS':
        return '', 200  # Si es un preflight request para CORS

    try:
        data = request.get_json()

        id_recibido = data.get('id')
        nombre_recibido = data.get('nombre')
        id_empleado = data.get('id_empleado')
        accion = data.get('accion')
        activo = data.get('activo')

        if not id_recibido or not nombre_recibido:
            return jsonify({'error': 'Se requieren los campos id y nombre'}), 400

        fecha_actual = datetime.now()

        # Primero buscar en tabla Encargado
        encargado = Encargado.query.filter_by(id=id_recibido).first()
        if encargado and encargado.nombre.strip().lower() == nombre_recibido.strip().lower():
            id_encargado = encargado.id
        else:
            # Si no coincide o no se encuentra, buscar en tabla Usuario
            usuario = Usuario.query.filter_by(id=id_recibido).first()
            if not usuario or usuario.nombre.strip().lower() != nombre_recibido.strip().lower():
                return jsonify({'error': 'No se encontró un encargado o usuario con el id y nombre proporcionados'}), 404
            id_encargado = usuario.id

        nueva_notificacion = Notificacion(
            id_encargado=id_encargado,
            id_empleado=id_empleado,
            accion=accion,
            fecha=fecha_actual
        )
        db.session.add(nueva_notificacion)
        db.session.commit()

        return jsonify({'message': 'Notificación creada correctamente'}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error al crear la notificacion: {e}")
        return jsonify({'error': str(e)}), 500

# -------------------------------ELIMINAR NOTIFICACIONES-------------------------------------
@notis_bp.route('/notificaciones/eliminar', methods=['OPTIONS', 'POST'])
def eliminar_notificacion():

    # 1. Verificar el tipo de solicitud
    if request.method == 'OPTIONS':
        return '', 200  # Si es un preflight request para CORS

    try:
        data = request.get_json()

        if not data or 'id' not in data:
            return jsonify({'error': 'Falta el id de la notificación'}), 400

        notificacion_id = data['id']

        notificacion = Notificacion.query.get(notificacion_id)

        if not notificacion:
            return jsonify({'error': 'Notificación no encontrada'}), 404

        notificacion.activo = False

        db.session.commit()

        return jsonify({'message': 'Notificación eliminada correctamente'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar la notificacion: {e}")
        return jsonify({'error': str(e)}), 500

    


# --------------- OBTENER NOTIFICACIONES ----------------------------------------------------------
@notis_bp.route('/notificaciones', methods=['OPTIONS', 'GET'])
def obtener_notificaciones():

    encargado_id = request.args.get('encargado_id', type=int)
    if not encargado_id:
        return jsonify({'error': 'Falta el parámetro encargado_id'}), 400

    fecha_limite = datetime.utcnow() - timedelta(days=60) # 60 dias atras desde hoy

    notificaciones = Notificacion.query.filter(
        Notificacion.id_encargado == encargado_id,
        Notificacion.fecha >= fecha_limite
    ).all()

    if not notificaciones:
        return jsonify({'message': 'No hay notificaciones'}), 404

    notificaciones_data = []
    for notificacion in notificaciones:
        notificaciones_data.append({
            'id': notificacion.id,
            'activo': notificacion.activo,
            'id_encargado': notificacion.id_encargado,
            'id_empleado': notificacion.id_empleado,
            'accion': notificacion.accion,
            'fecha': notificacion.fecha.strftime('%Y-%m-%d %H:%M:%S')
        })

    return jsonify({'notificaciones': notificaciones_data}), 200

@notis_bp.route('/notificaciones-usuario', methods=['OPTIONS', 'GET'])
def obtener_notificacionesUsuario():

    usuario_id = request.args.get('usuario_id', type=int)
    if not usuario_id:
        return jsonify({'error': 'Falta el parámetro usuario_id'}), 400

    fecha_limite = datetime.utcnow() - timedelta(days=60) # 60 dias atras desde hoy

    notificaciones = Notificacion.query.filter(
        Notificacion.id_encargado == usuario_id,
        Notificacion.fecha >= fecha_limite
    ).all()

    if not notificaciones:
        return jsonify({'message': 'No hay notificaciones'}), 404

    notificaciones_data = []
    for notificacion in notificaciones:
        notificaciones_data.append({
            'id': notificacion.id,
            'activo': notificacion.activo,
            'id_encargado': notificacion.id_encargado,
            'id_empleado': notificacion.id_empleado,
            'accion': notificacion.accion,
            'fecha': notificacion.fecha.strftime('%Y-%m-%d %H:%M:%S')
        })

    return jsonify({'notificaciones': notificaciones_data}), 200

# --------------- ELIMINACION DE NOTIFICACIONES TODAS ----------------------------------------------------------
@notis_bp.route('/notificaciones/eliminar-todas', methods=['OPTIONS','POST'])
def eliminar_todas_notificaciones():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        ids = data.get('ids', [])

        if not ids:
            return jsonify({'error': 'Se requieren IDs de notificaciones'}), 400

        # Desactivar solo las notificaciones con IDs recibidos y activas
        stmt = update(Notificacion).where(
            Notificacion.id.in_(ids),
            Notificacion.activo == True
        ).values(activo=False)

        result = db.session.execute(stmt)
        db.session.commit()

        return jsonify({
            "message": f"{result.rowcount} notificaciones desactivadas",
            "ids": ids
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error desactivando notificaciones: {str(e)}")
        return jsonify({"error": "Error al desactivar notificaciones"}), 500