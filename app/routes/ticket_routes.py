import os
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from app.models import Ticket, db
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.utils import enviar_correo

tickets_bp = Blueprint('tickets_bp', __name__)

DEPARTAMENTO_DESTINATARIOS = {
    'sistemas': ['sistemas.sl@araizahoteles.com'],
    'mantenimiento': ['mantenimientosanluis@araizahoteles.com'],
    'ama de llaves': ['amadellaves.sanluis@araizahoteles.com'],
    'seguridad': ['sehsl@araizahoteles.com'],
    'ayb': ['aybsanluis@araizahoteles.com'],
    'recepcion': ['recepcionsanluis@araizahoteles.com']
}

@tickets_bp.route('/nuevo', methods=['POST'])
def crear_ticket():
    # Detectar formato y extraer datos
    data = request.get_json(silent=True) if request.is_json else request.form

    # Normalizar y extraer campos
    titulo = (data.get('titulo') or '').strip()
    descripcion = (data.get('descripcion') or '').strip()
    departamento = (data.get('departamento') or '').strip()

    # usuario_id puede venir en form-data o también en query; tomar cualquiera
    usuario_id_raw = data.get('usuario_id') or request.args.get('usuario_id')
    try:
        usuario_id = int(str(usuario_id_raw).strip()) if usuario_id_raw is not None and str(usuario_id_raw).strip() != '' else None
    except (ValueError, TypeError):
        usuario_id = None

    # Validación detallada para identificar campos faltantes
    faltantes = []
    if not titulo:
        faltantes.append('titulo')
    if not descripcion:
        faltantes.append('descripcion')
    if not departamento:
        faltantes.append('departamento')
    if not usuario_id:
        faltantes.append('usuario_id')

    if faltantes:
        return jsonify({'error': 'Faltan campos requeridos', 'campos': faltantes}), 400

    nuevo_ticket = Ticket(
        titulo=titulo,
        descripcion=descripcion,
        departamento=departamento,
        estado='Abierto',
        usuario_id=usuario_id
    )

    db.session.add(nuevo_ticket)
    db.session.commit()

     # Enviar correo según casos configurados
    try:
        dep_key = (departamento or '').strip().lower()
        destinatarios = DEPARTAMENTO_DESTINATARIOS.get(dep_key, [])

        if destinatarios:
            asunto = f"Nuevo ticket en el departamento de {dep_key.capitalize()}"
            fecha_str = nuevo_ticket.fecha_creacion.strftime('%d/%m/%Y') if nuevo_ticket.fecha_creacion else ''
            # Construir enlace de seguimiento (usa el BASE URL configurado; ajusta por tu dominio)
            base_url = current_app.config.get('SITIO_BASE_URL', 'https://evaluacioneseva.com/login')
            link_seguimiento = f"{base_url}"

            cuerpo = (
                f"Se ha creado un nuevo ticket:\n\n"
                f"Título: {titulo}\n"
                f"Descripción: {descripcion}\n"
                f"Creado por: {nuevo_ticket.usuario_rel.nombre}\n"
                f"Estado: Abierto\n"
                f"Fecha de creación: {fecha_str}\n"
                f"Seguimiento: {link_seguimiento}\n"
            )

            # Versión HTML opcional (mejor presentación en clientes de correo)
            cuerpo_html = f"""
                <p>Se ha creado un nuevo ticket:</p>
                <ul>
                    <li><strong>Título:</strong> {titulo}</li>
                    <li><strong>Descripción:</strong> {descripcion}</li>
                    <li><strong>Creado por:</strong> {nuevo_ticket.usuario_rel.nombre}</li>
                    <li><strong>Estado:</strong> Abierto</li>
                    <li><strong>Fecha de creación:</strong> {fecha_str}</li>
                </ul>
                <p><a href="{link_seguimiento}" target="_blank">Ver y dar seguimiento al ticket</a></p>
            """

            enviar_correo(destinatarios, asunto, cuerpo, mensaje_html=cuerpo_html)
    except Exception as e:
        current_app.logger.exception("❌ Error al enviar correo de ticket: %s", e)

    return jsonify({
        'message': 'Ticket creado correctamente',
        'ticket_id': nuevo_ticket.id
    }), 200


@tickets_bp.route('/obtener-tickets', methods=['GET'])
def obtener_tickets():
    usuario_id = request.args.get('usuario_id', type=int)
    departamento_param = request.args.get('departamento', type=str)

    if not usuario_id:
        return jsonify({'error': 'Falta el ID del usuario'}), 400

    # Obtener usuario y rol
    from app.models import Usuario, Encargado, Ticket, db
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    # Mapeo de puesto → departamento destino (para encargados)
    puesto_a_departamento = {
        'encargado mantenimiento': 'Mantenimiento',
        'ama de llaves': 'Ama de llaves',
        'seguridad y bienestar': 'Seguridad',
        'ayb': 'AyB',
        'jefe de recepción': 'Recepcion'
    }

    def normalizar(s):
        return s.strip().lower() if isinstance(s, str) else ''

    # Determinar el departamento autorizado por el usuario
    dept_autorizado = None
    if usuario.rol_id == 1:
        # Rol Sistemas: solo ve tickets del departamento Sistemas (igual que tu lógica actual)
        dept_autorizado = 'Sistemas'
    else:
        # Intentar por encargado asociado
        encargado = Encargado.query.filter(Encargado.usuario_id == usuario_id).first()
        if encargado:
            dept_autorizado = puesto_a_departamento.get(normalizar(encargado.puesto))
        else:
            # Fallback para usuarios visualizadores (no encargados): por nombre de usuario
            dept_autorizado = visualizador_nombre_a_departamento.get(normalizar(usuario.nombre))

    # Si el cliente pide un departamento específico, validarlo contra el autorizado
    if departamento_param:
        if not dept_autorizado:
            return jsonify({'error': 'No se determinó el departamento autorizado para el usuario'}), 400

        if normalizar(departamento_param) != normalizar(dept_autorizado):
            return jsonify({'error': 'Departamento no autorizado para este usuario'}), 403

        departamento_objetivo = departamento_param
    else:
        if not dept_autorizado:
            return jsonify({'error': 'No se determinó el departamento autorizado para el usuario'}), 400
        departamento_objetivo = dept_autorizado

    # Consulta
    tickets = Ticket.query.filter(
        db.func.lower(Ticket.departamento) == normalizar(departamento_objetivo)
    ).all()

    # Respuesta
    resultado = []
    for ticket in tickets:
        resultado.append({
            'id': ticket.id,
            'titulo': ticket.titulo,
            'descripcion': ticket.descripcion,
            'departamento': getattr(ticket, 'departamento', None),
            'estado': ticket.estado,
            'fecha_creacion': ticket.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_creacion else None,
            'fecha_cierre': ticket.fecha_cierre.strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_cierre else None,
            'usuario_id': ticket.usuario_id,
            'usuario_nombre': ticket.usuario_rel.nombre if ticket.usuario_rel else None,
            'asignado_a_id': ticket.asignado_a,
            'asignado_a_nombre': ticket.empleado_rel.nombre if ticket.empleado_rel else None
        })

    return jsonify(resultado), 200

@tickets_bp.route('/obtener-tickets-por-departamento', methods=['GET'])
def obtener_tickets_por_departamento():
    usuario_id = request.args.get('usuario_id', type=int)
    departamento_param = request.args.get('departamento', type=str)

    if not usuario_id:
        return jsonify({'error': 'Falta el ID del usuario'}), 400
    if not departamento_param:
        return jsonify({'error': 'Falta el parámetro departamento'}), 400

    from app.models import Usuario, Encargado, Ticket, db
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    # Este servicio es para usuarios que NO son de Sistemas ni Encargados
    if usuario.rol_id == 1:
        return jsonify({'error': 'No autorizado en este servicio (Sistemas)'}), 403

    encargado = Encargado.query.filter(Encargado.usuario_id == usuario_id).first()
    if encargado:
        return jsonify({'error': 'No autorizado en este servicio (Encargado)'}), 403

    def normalizar(s):
        return s.strip().lower() if isinstance(s, str) else ''

    # Filtrar exclusivamente por el departamento proporcionado
    tickets = Ticket.query.filter(
        db.func.lower(Ticket.departamento) == normalizar(departamento_param)
    ).all()

    resultado = []
    for ticket in tickets:
        resultado.append({
            'id': ticket.id,
            'titulo': ticket.titulo,
            'descripcion': ticket.descripcion,
            'departamento': getattr(ticket, 'departamento', None),
            'estado': ticket.estado,
            'fecha_creacion': ticket.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_creacion else None,
            'fecha_cierre': ticket.fecha_cierre.strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_cierre else None,
            'usuario_id': ticket.usuario_id,
            'usuario_nombre': ticket.usuario_rel.nombre if ticket.usuario_rel else None,
            'asignado_a_id': ticket.asignado_a,
            'asignado_a_nombre': ticket.empleado_rel.nombre if ticket.empleado_rel else None
        })

    return jsonify(resultado), 200    


@tickets_bp.route('/tipo-tickets', methods=['GET'])
def obtener_tipos_tickets():
    from app.models import TipoTicket  # Asegúrate que esté bien importado tu modelo

    tipos = TipoTicket.query.all()
    resultado = [{'id': tipo.id, 'nombre': tipo.nombre} for tipo in tipos]

    return jsonify(resultado), 200

@tickets_bp.route('/detalle-ticket/<int:ticket_id>', methods=['GET'])
def detalle_ticket(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket no encontrado'}), 404

    resultado = {
        'id': ticket.id,
        'titulo': ticket.titulo,
        'descripcion': ticket.descripcion,
        'departamento': ticket.departamento,
        'estado': ticket.estado,
        'fecha_creacion': ticket.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_creacion else None,
        'fecha_cierre': ticket.fecha_cierre.strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_cierre else None
        # Eliminado: 'imagen'
    }
    return jsonify(resultado), 200

@tickets_bp.route('/actualizar-estado/<int:ticket_id>', methods=['PUT'])
def actualizar_estado_ticket(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket no encontrado'}), 404

    data = request.get_json(silent=True) or {}
    nuevo_estado = data.get('estado')

    if not nuevo_estado:
        return jsonify({'error': 'Se requiere el campo estado'}), 400

    ticket.estado = nuevo_estado

    if nuevo_estado.lower() == 'concluido':
        ticket.fecha_cierre = datetime.utcnow()
    else:
        ticket.fecha_cierre = None

    db.session.commit()

    return jsonify({
        'message': 'Estado actualizado correctamente',
        'ticket': {
            'id': ticket.id,
            'estado': ticket.estado,
            'fecha_cierre': ticket.fecha_cierre.strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_cierre else None
        }
    }), 200

@tickets_bp.route('/asignar', methods=['POST'])
def asignar_empleado_a_ticket():
    data = request.get_json(silent=True) or {}
    ticket_id = data.get('ticket_id')
    empleado_id = data.get('empleado_id')

    if not ticket_id or not empleado_id:
        return jsonify({'error': 'Faltan campos requeridos: ticket_id y empleado_id'}), 400

    # Validaciones de tipos
    try:
        ticket_id = int(ticket_id)
        empleado_id = int(empleado_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'ticket_id y empleado_id deben ser enteros'}), 400

    # Buscar ticket y empleado
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket no encontrado'}), 404

    from app.models import Empleado
    empleado = Empleado.query.get(empleado_id)
    if not empleado or not empleado.activo:
        return jsonify({'error': 'Empleado no encontrado o inactivo'}), 404

    # Asignar
    ticket.asignado_a = empleado_id
    db.session.commit()

    return jsonify({
        'message': 'Ticket asignado correctamente',
        'ticket_id': ticket.id,
        'asignado_a_id': ticket.asignado_a,
        'asignado_a_nombre': empleado.nombre,
        'estado_actual': ticket.estado
    }), 200

@tickets_bp.route('/cambiar-estado', methods=['POST'])
def cambiar_estado_ticket():
    data = request.get_json(silent=True) or {}
    ticket_id = data.get('ticket_id')
    nuevo_estado = data.get('estado')

    if not ticket_id or not nuevo_estado:
        return jsonify({'error': 'Faltan campos requeridos: ticket_id y estado'}), 400

    try:
        ticket_id = int(ticket_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'ticket_id debe ser entero'}), 400

    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket no encontrado'}), 404

    # Actualizar estado y fecha de cierre
    ticket.estado = nuevo_estado
    if nuevo_estado.strip().lower() == 'concluido':
        ticket.fecha_cierre = datetime.utcnow()
    else:
        ticket.fecha_cierre = None

    db.session.commit()

    return jsonify({
        'message': 'Estado actualizado correctamente',
        'ticket': {
            'id': ticket.id,
            'estado': ticket.estado,
            'fecha_cierre': ticket.fecha_cierre.strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_cierre else None
        }
    }), 200
