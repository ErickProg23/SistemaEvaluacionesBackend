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

    return jsonify({'message': 'Ticket creado correctamente', 'ticket_id': nuevo_ticket.id}), 201.

@tickets_bp.route('/tipo-tickets', methods=['GET'])
def obtener_tipos_tickets():
    from app.models import TipoTicket  # Asegúrate que esté bien importado tu modelo

    tipos = TipoTicket.query.all()
    resultado = [{'id': tipo.id, 'nombre': tipo.nombre} for tipo in tipos]

    return jsonify(resultado), 200
