import os
from flask import Blueprint, request, jsonify
from datetime import datetime
from app.models import Ticket, db
from werkzeug.utils import secure_filename



tickets_bp = Blueprint('tickets_bp', __name__)

# Define la carpeta uploads relativa al nivel de tu proyecto
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')

# Asegúrate que exista la carpeta
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@tickets_bp.route('/nuevo', methods=['POST'])
def crear_ticket():
    data = request.form
    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    departamento = data.get('departamento')
    usuario_id = data.get('usuario_id')

    if not titulo or not descripcion or not departamento or not usuario_id:
        return jsonify({'error': 'Faltan campos requeridos'}), 400

    imagen = request.files.get('imagen')
    nombre_imagen = None
    if imagen:
        nombre_imagen = secure_filename(imagen.filename)
        imagen.save(os.path.join(UPLOAD_FOLDER, nombre_imagen))

    nuevo_ticket = Ticket(
        titulo=titulo,
        descripcion=descripcion,
        departamento=departamento,
        estado='Abierto',
        usuario_id=int(usuario_id),
        imagen=nombre_imagen
    )

    db.session.add(nuevo_ticket)
    db.session.commit()

    return jsonify({'message': 'Ticket creado correctamente', 'ticket_id': nuevo_ticket.id}), 200



@tickets_bp.route('/obtener-tickets', methods=['GET'])
def obtener_tickets():
    usuario_id = request.args.get('usuario_id', type=int)
    if not usuario_id:
        return jsonify({'error': 'Falta el ID del usuario'}), 400

    # Obtener rol del usuario
    from app.models import Usuario
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    # Rol 1: ver tickets del departamento "Sistemas"
    if usuario.rol_id == 1:
        tickets = Ticket.query.filter(Ticket.departamento == 'Sistemas').all()
    else:
        # Otros roles: ver tickets creados por el usuario
        tickets = Ticket.query.filter(Ticket.usuario_id == usuario_id).all()

    resultado = []
    for ticket in tickets:
        resultado.append({
            'id': ticket.id,
            'titulo': ticket.titulo,
            'descripcion': ticket.descripcion,
            'usuario_id': ticket.usuario_id,
            'departamento': getattr(ticket, 'departamento', None),
            'estado': ticket.estado,
            'fecha_creacion': ticket.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_creacion else None,
            'fecha_cierre': ticket.fecha_cierre.strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_cierre else None,
            'imagen': ticket.imagen
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
        'fecha_cierre': ticket.fecha_cierre.strftime('%Y-%m-%d %H:%M:%S') if ticket.fecha_cierre else None,
        'imagen': ticket.imagen
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
