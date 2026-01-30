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

    # Obtener los IDs de usuario reales para consultar NotificacionTicket
    user_ids = []
    if usuario_id:
        user_ids.append(usuario_id)
    
    if id_encargado:
        encargado_obj = Encargado.query.get(id_encargado)
        if encargado_obj and encargado_obj.usuario_id:
            user_ids.append(encargado_obj.usuario_id)

    def generate():
        # Estado local para rastrear qué hemos enviado y detectar cambios
        # Estructura: 
        # { 
        #   'general': { id_notificacion: { 'activo': bool } },
        #   'ticket': { id_notificacion: { 'leido': bool, 'mensajes': int, 'ultimo': str } }
        # }
        known_state = {
            'general': {},
            'ticket': {}
        }
        
        # Fecha límite para no cargar historia antigua

        # Ajustable según necesidad, pero para realtime suele interesar lo reciente.
        # El frontend ya carga el historial con los otros endpoints.
        # Sin embargo, si el usuario refresca, querrá ver lo actual.
        # Usaremos la misma lógica de historial reciente (60 días) para mantener consistencia.
        
        try:
            while True:
                # Forzar una transacción fresca para ver cambios de otros usuarios inmediatamente
                # Aunque remove() ayuda, un commit() vacío asegura que no estamos en una transacción stale 'REPEATABLE READ'
                try:
                    db.session.commit()
                except:
                    db.session.rollback()

                fecha_limite = datetime.utcnow() - timedelta(days=60)
                
                # Consultar DB - Notificaciones Generales
                # Usamos filter(Notificacion.id_encargado.in_(target_ids)) para cubrir ambos casos
                notificaciones = Notificacion.query.filter(
                    Notificacion.id_encargado.in_(target_ids),
                    Notificacion.fecha >= fecha_limite
                ).all()

                # Consultar DB - Notificaciones de Tickets
                notificaciones_tickets = []
                if user_ids:
                    notificaciones_tickets = NotificacionTicket.query.filter(
                        NotificacionTicket.usuario_id.in_(user_ids),
                        NotificacionTicket.fecha_actualizacion >= fecha_limite
                    ).all()

                data_sent = False

                # Procesar Notificaciones Generales
                for noti in notificaciones:
                    noti_id = noti.id
                    is_active = noti.activo
                    
                    # Determinar si debemos enviar este evento
                    should_send = False
                    
                    if noti_id not in known_state['general']:
                        # Nueva notificación encontrada
                        should_send = True
                        known_state['general'][noti_id] = {'activo': is_active}
                    elif known_state['general'][noti_id]['activo'] != is_active:
                        # El estado cambió
                        should_send = True
                        known_state['general'][noti_id]['activo'] = is_active
                    
                    if should_send:
                        # Mapeo de acciones a texto legible
                        mapa_mensajes = {
                            1: "Alta de empleado",
                            2: "Baja de empleado",
                            3: "Evaluación completada",
                            4: "Evaluación atrasada",
                            5: "Nuevo Ticket Asignado"
                        }
                        mensaje_texto = mapa_mensajes.get(noti.accion, "Notificación actualizada")

                        # Construir payload
                        payload = {
                            "id": noti.id,
                            "tipo": "general",
                            "accion": noti.accion,
                            "fecha": noti.fecha.isoformat(),
                            "activo": noti.activo,
                            "notificacion": {
                                "id": noti.id,
                                "id_encargado": noti.id_encargado,
                                "id_empleado": noti.id_empleado,
                                "mensaje": mensaje_texto
                            }
                        }
                        
                        yield f"data: {json.dumps(payload)}\n\n"
                        data_sent = True

                # Procesar Notificaciones de Tickets
                for noti_t in notificaciones_tickets:
                    t_id = noti_t.id
                    leido = noti_t.leido
                    cantidad = noti_t.cantidad_mensajes
                    ultimo = noti_t.ultimo_mensaje

                    should_send_t = False

                    if t_id not in known_state['ticket']:
                        should_send_t = True
                        known_state['ticket'][t_id] = {
                            'leido': leido,
                            'mensajes': cantidad,
                            'ultimo': ultimo
                        }
                    else:
                        prev = known_state['ticket'][t_id]
                        if prev['leido'] != leido or prev['mensajes'] != cantidad or prev['ultimo'] != ultimo:
                            should_send_t = True
                            prev['leido'] = leido
                            prev['mensajes'] = cantidad
                            prev['ultimo'] = ultimo
                    
                    if should_send_t:
                        # Construir payload para ticket
                        # Reutilizamos estructura compatible o enviamos objeto distinto con 'tipo'
                        payload = noti_t.to_dict()
                        # to_dict ya incluye 'tipo': 'ticket_chat'
                        
                        yield f"data: {json.dumps(payload)}\n\n"
                        data_sent = True

                # Importante: Liberar sesión para asegurar datos frescos en la siguiente vuelta


                # Importante: Liberar sesión para asegurar datos frescos en la siguiente vuelta
                # y no saturar el pool de conexiones
                db.session.remove()
                
                # Keep-Alive: Enviar un comentario para mantener la conexión activa y forzar flush del buffer
                yield ": ping\n\n"
                
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
        tipo = data.get('tipo', 'general') # 'general' o 'ticket_chat'

        # Caso 1: Notificación de Chat de Ticket
        if tipo == 'ticket_chat':
            notif_ticket = NotificacionTicket.query.get(notificacion_id)
            if notif_ticket:
                notif_ticket.leido = True
                db.session.commit()
                return jsonify({'message': 'Notificación de ticket marcada como leída'}), 200
            else:
                return jsonify({'error': 'Notificación de ticket no encontrada'}), 404

        # Caso 2: Notificación General (Default)
        else:
            notificacion = Notificacion.query.get(notificacion_id)
            if not notificacion:
                # Fallback: Intentar buscar en tickets si no se encontró en general
                notif_ticket = NotificacionTicket.query.get(notificacion_id)
                if notif_ticket:
                    notif_ticket.leido = True
                    db.session.commit()
                    return jsonify({'message': 'Notificación de ticket marcada como leída (fallback)'}), 200
                
                return jsonify({'error': 'Notificación no encontrada'}), 404

            notificacion.activo = False
            db.session.commit()
            return jsonify({'message': 'Notificación eliminada correctamente'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar la notificacion: {e}")
        return jsonify({'error': str(e)}), 500


@notis_bp.route('/notificaciones/marcar-todas-leidas', methods=['POST'])
def marcar_todas_leidas():
    try:
        data = request.get_json()
        usuario_id = data.get('usuario_id')
        id_encargado = data.get('id_encargado')

        if not usuario_id and not id_encargado:
            return jsonify({'error': 'Se requiere usuario_id o id_encargado'}), 400

        target_ids = []
        user_ids = []

        if usuario_id:
            target_ids.append(usuario_id)
            user_ids.append(usuario_id)
        
        if id_encargado:
            target_ids.append(id_encargado)
            enc = Encargado.query.get(id_encargado)
            if enc and enc.usuario_id:
                user_ids.append(enc.usuario_id)

        if target_ids:
            Notificacion.query.filter(
                Notificacion.id_encargado.in_(target_ids),
                Notificacion.activo == True
            ).update({Notificacion.activo: False}, synchronize_session=False)

        if user_ids:
            NotificacionTicket.query.filter(
                NotificacionTicket.usuario_id.in_(user_ids),
                NotificacionTicket.leido == False
            ).update({NotificacionTicket.leido: True}, synchronize_session=False)

        db.session.commit()
        return jsonify({'message': 'Todas las notificaciones marcadas como leídas'}), 200

    except Exception as e:
        db.session.rollback()
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

    # Lógica para obtener IDs de usuario para buscar en NotificacionTicket
    user_ids = []
    if usuario_id:
        user_ids.append(usuario_id)
    
    if encargado_id:
        encargado_obj = Encargado.query.get(encargado_id)
        if encargado_obj and encargado_obj.usuario_id:
            user_ids.append(encargado_obj.usuario_id)

    fecha_limite = datetime.utcnow() - timedelta(days=60) # 60 dias atras desde hoy

    notificaciones = Notificacion.query.filter(
        Notificacion.id_encargado.in_(target_ids),
        Notificacion.fecha >= fecha_limite
    ).all()

    notificaciones_tickets = []
    if user_ids:
        notificaciones_tickets = NotificacionTicket.query.filter(
            NotificacionTicket.usuario_id.in_(user_ids),
            NotificacionTicket.fecha_actualizacion >= fecha_limite
        ).all()

    if not notificaciones and not notificaciones_tickets:
        # Retornar lista vacía en lugar de 404 para evitar errores en frontend
        return jsonify({'notificaciones': []}), 200

    notificaciones_data = []
    
    # Procesar Notificaciones Generales
    for notificacion in notificaciones:
        notificaciones_data.append({
            'id': notificacion.id,
            'tipo': 'general',
            'activo': notificacion.activo,
            'id_encargado': notificacion.id_encargado,
            'id_empleado': notificacion.id_empleado,
            'accion': notificacion.accion,
            'fecha': notificacion.fecha.strftime('%Y-%m-%d %H:%M:%S')
        })

    # Procesar Notificaciones de Tickets
    for nt in notificaciones_tickets:
        notificaciones_data.append({
            'id': nt.id,
            'tipo': 'ticket_chat',
            # Mapeamos 'leido' a 'activo' (inverso) para compatibilidad con lógica de UI de "borrar/ocultar"
            'activo': not nt.leido, 
            'leido': nt.leido,
            'fecha': nt.fecha_actualizacion.strftime('%Y-%m-%d %H:%M:%S'),
            'ticket_id': nt.ticket_id,
            'titulo': nt.ticket_rel.titulo if nt.ticket_rel else 'Ticket',
            'mensaje': f"Nuevo mensaje: {nt.ultimo_mensaje}" if nt.ultimo_mensaje else "Nuevo mensaje en ticket",
            'cantidad_mensajes': nt.cantidad_mensajes
        })

    # Ordenar combinadas por fecha descendente
    notificaciones_data.sort(key=lambda x: x['fecha'], reverse=True)

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

    # Buscar también notificaciones de tickets para este usuario
    notificaciones_tickets = NotificacionTicket.query.filter(
        NotificacionTicket.usuario_id == usuario_id,
        NotificacionTicket.fecha_actualizacion >= fecha_limite
    ).all()

    if not notificaciones and not notificaciones_tickets:
        return jsonify({'message': 'No hay notificaciones'}), 404

    notificaciones_data = []
    
    # Procesar Notificaciones Generales
    for notificacion in notificaciones:
        notificaciones_data.append({
            'id': notificacion.id,
            'tipo': 'general',
            'activo': notificacion.activo,
            'id_encargado': notificacion.id_encargado,
            'id_empleado': notificacion.id_empleado,
            'accion': notificacion.accion,
            'fecha': notificacion.fecha.strftime('%Y-%m-%d %H:%M:%S')
        })

    # Procesar Notificaciones de Tickets
    for nt in notificaciones_tickets:
        notificaciones_data.append({
            'id': nt.id,
            'tipo': 'ticket_chat',
            'activo': not nt.leido,
            'leido': nt.leido,
            'fecha': nt.fecha_actualizacion.strftime('%Y-%m-%d %H:%M:%S'),
            'ticket_id': nt.ticket_id,
            'titulo': nt.ticket_rel.titulo if nt.ticket_rel else 'Ticket',
            'mensaje': f"Nuevo mensaje: {nt.ultimo_mensaje}" if nt.ultimo_mensaje else "Nuevo mensaje en ticket",
            'cantidad_mensajes': nt.cantidad_mensajes
        })

    # Ordenar por fecha descendente
    notificaciones_data.sort(key=lambda x: x['fecha'], reverse=True)

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


    