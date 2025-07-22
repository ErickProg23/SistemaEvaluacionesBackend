import os
from flask import Blueprint, request, jsonify
from datetime import datetime
from app.models import Ticket, TipoTicket, db
from werkzeug.utils import secure_filename



tickets_bp = Blueprint('tickets_bp', __name__)

# Define la carpeta uploads relativa al nivel de tu proyecto
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')

# Asegúrate que exista la carpeta
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@tickets_bp.route('/nuevo', methods=['POST'])
def crear_ticket():
    data = request.form  # Para recibir datos + archivos juntos, mejor usar form
    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    tipo_ticket_id = data.get('tipo')
    usuario_id = data.get('usuario_id')

    if not titulo or not descripcion or not tipo_ticket_id or not usuario_id:
        return jsonify({'error': 'Faltan campos requeridos'}), 400

    imagen = request.files.get('imagen')
    nombre_imagen = None

    if imagen:
        # Sanear el nombre del archivo
        nombre_imagen = secure_filename(imagen.filename)
        # Guardar el archivo en la carpeta uploads
        imagen.save(os.path.join(UPLOAD_FOLDER, nombre_imagen))

    nuevo_ticket = Ticket(
        titulo=titulo,
        descripcion=descripcion,
        tipo_ticket=tipo_ticket_id,
        estado='Abierto',
        usuario_id=usuario_id,
        asignado_a=1,
        imagen=nombre_imagen  # Guarda el nombre del archivo en la BD
    )

    db.session.add(nuevo_ticket)
    db.session.commit()

    return jsonify({'message': 'Ticket creado correctamente', 'ticket_id': nuevo_ticket.id}), 200



@tickets_bp.route('/obtener-tickets', methods=['GET'])
def obtener_tickets():
    usuario_id = request.args.get('usuario_id')
    if not usuario_id:
        return jsonify({'error': 'Falta el ID del usuario'}), 400

    tickets = Ticket.query.filter_by(usuario_id=usuario_id).all()
    resultado = []

    for ticket in tickets:
        resultado.append({
            'id': ticket.id,
            'titulo': ticket.titulo,
            'descripcion': ticket.descripcion,
            'tipo_ticket': ticket.tipo_ticket_rel.nombre if ticket.tipo_ticket_rel else None,
            'estado': ticket.estado,
            'fecha_creacion': ticket.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S'),
            'asignado_a': ticket.asignado_a,
            'usuario': {
                'id': ticket.usuario_rel.id,
                'nombre': ticket.usuario_rel.nombre
            } if ticket.usuario_rel else None
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
        'tipo_ticket': ticket.tipo_ticket_rel.nombre if ticket.tipo_ticket_rel else None,
        'estado': ticket.estado,
        'fecha_creacion': ticket.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S'),
        'asignado_a': ticket.asignado_a,
        'imagen': ticket.imagen  # nombre o ruta del archivo
    }
    return jsonify(resultado), 200
