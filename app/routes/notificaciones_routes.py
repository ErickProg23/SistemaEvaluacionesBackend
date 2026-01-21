from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.models import Empleado, Encargado, Usuario, Pregunta, Notificacion, NotificacionTicket, Ticket, MensajeTicket
from app import db
from sqlalchemy import update
from datetime import datetime, timedelta
import time
import json

# Definición del Blueprint para las rutas de obtención de datos
notis_bp = Blueprint('notis_bp', __name__)


#----------------------------NOTIFICACIONES REALTIME (SSE)---------------------------------------
@notis_bp.route('/realtime', methods=['GET'])
def realtime_notificaciones():
    usuario_id = request.args.get('usuario_id', type=int)
    id_encargado = request.args.get('id_encargado', type=int)

    if not usuario_id and not id_encargado:
        return jsonify({'error': 'Se requiere usuario_id o id_encargado'}), 400

    # Determinar qué IDs vamos a monitorear en la columna id_encargado
    target_ids = []
    if usuario_id:
        target_ids.append(usuario_id)
    if id_encargado:
        target_ids.append(id_encargado)

    def generate():
        # Estado local para rastrear qué hemos enviado y detectar cambios
        # Estructura: { id_notificacion: { 'activo': bool, 'enviado': bool } }
        known_state = {}
        
        # Fecha límite para no cargar historia antigua (ej. últimos 7 días para realtime)
        # Ajustable según necesidad, pero para realtime suele interesar lo reciente.
        # El frontend ya carga el historial con los otros endpoints.
        # Sin embargo, si el usuario refresca, querrá ver lo actual.
        # Usaremos la misma lógica de historial reciente (60 días) para mantener consistencia.
        
        try:
            while True:
                fecha_limite = datetime.utcnow() - timedelta(days=60)
                
                # Consultar DB
                # Usamos filter(Notificacion.id_encargado.in_(target_ids)) para cubrir ambos casos
                notificaciones = Notificacion.query.filter(
                    Notificacion.id_encargado.in_(target_ids),
                    Notificacion.fecha >= fecha_limite
                ).all()

                data_sent = False

                for noti in notificaciones:
                    noti_id = noti.id
                    is_active = noti.activo
                    
                    # Determinar si debemos enviar este evento
                    should_send = False
                    
                    if noti_id not in known_state:
                        # Nueva notificación encontrada en este ciclo (o primera carga)
                        should_send = True
                        known_state[noti_id] = {'activo': is_active}
                    elif known_state[noti_id]['activo'] != is_active:
                        # El estado cambió (ej. se eliminó/desactivó)
                        should_send = True
                        known_state[noti_id]['activo'] = is_active
                    
                    if should_send:
                        # Construir payload
                        payload = {
                            "id": noti.id,
                            "accion": noti.accion,
                            "fecha": noti.fecha.isoformat(),
                            "activo": noti.activo,
                            "notificacion": {
                                "id": noti.id,
                                "id_encargado": noti.id_encargado,
                                "id_empleado": noti.id_empleado,
                                "mensaje": "Notificación actualizada" # Opcional/Customizable
                            }
                        }
                        
                        # Formato SSE: data: <json>\n\n
                        yield f"data: {json.dumps(payload)}\n\n"
                        data_sent = True

                # Importante: Liberar sesión para asegurar datos frescos en la siguiente vuelta
                # y no saturar el pool de conexiones
                db.session.remove()
                
                # Si no se envió nada, podemos enviar un comentario 'keep-alive' opcional
                # yield ": keep-alive\n\n"
                
                time.sleep(3) # Polling cada 3 segundos

        except GeneratorExit:
            # Cliente se desconectó
            db.session.remove()
            pass
        except Exception as e:
            print(f"Error en SSE: {e}")
            db.session.remove()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


#----------------------------NOTIFICACIONES------------------------------------------------------
@notis_bp.route('/notificaciones/nueva', methods=['OPTIONS', 'POST'])
def nueva_notificacion():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()

        id_encargado = data.get('id_encargado')
        nombre_recibido = data.get('nombre')  # opcional
        id_empleado = data.get('id_empleado')
        accion = data.get('accion')
        activo = data.get('activo')

        if not id_encargado:
            return jsonify({'error': 'Se requiere el campo id'}), 400

        fecha_actual = datetime.now()

        # Buscar primero en Encargado por ID
        encargado = Encargado.query.filter_by(id=id_encargado).first()

        if encargado:
            if nombre_recibido:
                if encargado.nombre.strip().lower() != nombre_recibido.strip().lower():
                    return jsonify({'error': 'Nombre no coincide con el encargado'}), 400
            id_encargado = encargado.id
        else:
            # Buscar en Usuario por ID
            usuario = Usuario.query.filter_by(id=id_encargado).first()
            if not usuario:
                return jsonify({'error': 'No se encontró encargado ni usuario con el ID proporcionado'}), 404

            if nombre_recibido:
                if usuario.nombre.strip().lower() != nombre_recibido.strip().lower():
                    return jsonify({'error': 'Nombre no coincide con el usuario'}), 400

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
        print(f"Error al crear la notificación: {e}")
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

    encargado_id = request.args.get('encargado_id')
    usuario_id = request.args.get('usuario_id')
    
    # Normalizar valores "null" string que a veces envían los frontends
    if encargado_id == 'null' or encargado_id == 'undefined':
        encargado_id = None
    if usuario_id == 'null' or usuario_id == 'undefined':
        usuario_id = None

    if not encargado_id and not usuario_id:
        return jsonify({'error': 'Falta el parámetro encargado_id o usuario_id'}), 400

    # Convertir a int si existen
    if encargado_id: encargado_id = int(encargado_id)
    if usuario_id: usuario_id = int(usuario_id)

    target_ids = []
    if encargado_id:
        target_ids.append(encargado_id)
    # Si se envía usuario_id, también buscamos notificaciones dirigidas a ese ID
    # (ya que en tickets guardamos usuario_id en el campo id_encargado para admins)
    if usuario_id:
        target_ids.append(usuario_id)

    fecha_limite = datetime.utcnow() - timedelta(days=60) # 60 dias atras desde hoy

    notificaciones = Notificacion.query.filter(
        Notificacion.id_encargado.in_(target_ids),
        Notificacion.fecha >= fecha_limite
    ).all()

    if not notificaciones:
        # Retornar lista vacía en lugar de 404 para evitar errores en frontend
        return jsonify({'notificaciones': []}), 200

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

@notis_bp.route('/nueva/atrasada', methods=['OPTIONS', 'POST'])
def nueva_notificacion_atrasada():
    if request.method == 'OPTIONS':
        return '', 200


    try:
        data = request.get_json()

        id_encargado = data.get('id_encargado')
        accion = data.get('accion')
        activo = data.get('activo')

        if not id_encargado:
            return jsonify({'error': 'Se requiere el campo id'}), 400

        fecha_actual = datetime.now()

        nueva_notificacion = Notificacion(
            id_encargado=id_encargado,
            accion=accion,
            fecha=fecha_actual
        )
        db.session.add(nueva_notificacion)
        db.session.commit()

        return jsonify({'message': 'Notificación creada correctamente'}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error al crear la notificación: {e}")
        return jsonify({'error': str(e)}), 500


    