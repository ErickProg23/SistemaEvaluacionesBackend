from flask import Blueprint, request, jsonify
from datetime import datetime
from app.models import Ticket, TipoTicket, db


tickets_bp = Blueprint('tickets_bp', __name__)

@tickets_bp.route('/nuevo', methods=['POST'])
def crear_ticket():
    data = request.get_json()

    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    tipo_ticket_id = data.get('tipo')
    usuario_id = data.get('usuario_id')  # Asumes que se manda o lo puedes obtener del session

    if not titulo or not descripcion or not tipo_ticket_id or not usuario_id:
        return jsonify({'error': 'Faltan campos requeridos'}), 400

    nuevo_ticket = Ticket(
        titulo=titulo,
        descripcion=descripcion,
        tipo_ticket=tipo_ticket_id,
        estado='Abierto',
        usuario_id=usuario_id,
        asignado_a=1,
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
