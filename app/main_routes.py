from flask import Blueprint, jsonify, request, make_response, send_from_directory
from flask_jwt_extended import create_access_token, jwt_required
from .models import Usuario, Rol, Empleado, Encargado, Pregunta, Evaluacion, Notificacion, Formato, Evaluacion_Encargado
from flask_cors import CORS
from app import db
from collections import defaultdict
from datetime import datetime, timedelta, date
from sqlalchemy import func, update
import pytz
import os
from . import jwt, bcrypt  # Asegúrate de que `bcrypt` esté configurado en tu archivo principal


# Crear un Blueprint para las rutas
routes_blueprint = Blueprint('routes', __name__)


@jwt.user_identity_loader
def user_identity_lookup(user):
    return user  # Ajusta esto según el campo de identidad único de tu modelo de usuario


# --------------- CREAR REGISTRO DE ENCARGADO PARA USUARIO NUEVO ---------------------------
@routes_blueprint.route('/personal/nuevo-encargado', methods=['OPTIONS', 'POST'])
def crear_registro_encargado():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data.get('nombre') or not data.get('usuario_id'):
            return jsonify({'message': 'Faltan datos requeridos (nombre o usuario_id)'}), 400
        
        # Verificar si ya existe un encargado con ese usuario_id
        encargado_existente = Encargado.query.filter_by(usuario_id=data['usuario_id']).first()
        if encargado_existente:
            return jsonify({'message': 'Ya existe un encargado asociado a este usuario'}), 409
        
        # Crear nuevo encargado con datos básicos
        nuevo_encargado = Encargado(
            nombre=data['nombre'],
            usuario_id=data['usuario_id'],
            puesto='Pendiente',  # Valor por defecto
            num_empleado='Pendiente',  # Valor por defecto
            rol_id=2,  # ID para encargado
            activo=True
        )
        
        db.session.add(nuevo_encargado)
        db.session.commit()
        
        return jsonify({
            'message': 'Registro de encargado creado correctamente',
            'encargado': {
                'id': nuevo_encargado.id,
                'nombre': nuevo_encargado.nombre,
                'usuario_id': nuevo_encargado.usuario_id
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error al crear registro de encargado: {str(e)}'}), 500

@routes_blueprint.route('/ultimaFechaEvaluacion', methods=['OPTIONS', 'GET'])
def obtener_ultima_fecha_evaluacion():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        # Obtener la última fecha de evaluación
        id_encargado = request.args.get('id_encargado', type=int)
        semana = request.args.get('semana', type=int)

        if id_encargado is None or semana is None:
            return jsonify({'error': 'Faltan parámetros requeridos'}), 400

        evaluacion_existente = db.session.query(Evaluacion).filter_by(
            encargado_id=id_encargado, num_semana=semana
        ).first()

        #Si existe una evaluación, devolver true
        ya_evaluo = evaluacion_existente is not None
        return jsonify({'ya_evaluo': ya_evaluo}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@routes_blueprint.route('/usuarios/verificar/<int:num_empleado>', methods=['OPTIONS', 'GET'])
def verificar_numero_empleado(num_empleado):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Buscar en la tabla de empleados
        empleado = Empleado.query.filter_by(num_empleado=num_empleado).first()
        
        # Buscar en la tabla de encargados
        encargado = Encargado.query.filter_by(num_empleado=num_empleado).first()
        
        if empleado or encargado:
            # Si existe un empleado o encargado con ese número
            return jsonify({
                'existe': True,
                'mensaje': 'Ya existe un usuario con este número de empleado'
            }), 200
        else:
            # Si no existe
            return jsonify({
                'existe': False,
                'mensaje': 'Número de empleado disponible'
            }), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500



