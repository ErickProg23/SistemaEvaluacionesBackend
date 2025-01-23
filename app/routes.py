from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from .models import Usuario, Rol, Empleado, Encargado
from flask_cors import CORS
from app import db
from . import jwt, bcrypt  # Asegúrate de que `bcrypt` esté configurado en tu archivo principal


# Crear un Blueprint para las rutas
routes_blueprint = Blueprint('routes', __name__)

@jwt.user_identity_loader
def user_identity_lookup(user):
    return user  # Ajusta esto según el campo de identidad único de tu modelo de usuario

@routes_blueprint.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    correo = data.get('correo')
    contrasena = data.get('contrasena')

    # Busca al usuario en la base de datos
    usuario = Usuario.query.filter_by(correo=correo).first()

    if contrasena and usuario.contrasena == contrasena:
        # Generar un token de acceso
        access_token = create_access_token(identity={'correo': usuario.correo})
        return jsonify({'access_token': access_token}), 200

    return jsonify({'message': 'Correo o contraseña incorrectos'}), 401


@routes_blueprint.route('/usuarios/empleados', methods=['GET'])
def get_empleados():
    empleados = Empleado.query.all()

    # Verifica si se encontraron empleados
    if empleados:
        # Itera sobre la lista de empleados y crea un diccionario con los datos necesarios
        empleados_data = [{'id': empleado.id, 'nombre': empleado.nombre, 
                           'puesto': empleado.puesto, 'num_empleado': empleado.num_empleado, 'activo': empleado.activo}
                          for empleado in empleados]
        return jsonify(empleados_data), 200
    else:
        return jsonify({'message': 'No se pudo extraer la informacion'}), 401

@routes_blueprint.route('/usuarios/encargados', methods=['GET'])
def get_encargados():
    encargados = Encargado.query.all()
    # Verifica si se encontraron encargados

    if encargados:
        # Itera sobre la lista de encargados y crea un diccionario con los datos
        encargados_data = [{'id': encargado.id, 'nombre': encargado.nombre, 'activo': encargado.activo} 
                            for encargado in encargados]
        return jsonify(encargados_data), 200
    else:
        return jsonify({'message': 'No se pudo extraer la informacion'}), 401

@routes_blueprint.route('/usuarios/empleados/desactivar/<int:id>', methods=['OPTIONS', 'PUT'])
def deactivate_employee(id):    
    # Manejo del método PUT
    empleado = Empleado.query.get(id)
    if not empleado:
        return jsonify({'error': 'Empleado no encontrado'}), 404
    
    empleado.activo = False
    db.session.commit()
    return jsonify({'message': 'Empleado desactivado correctamente'})

@routes_blueprint.route('/empleados/nuevo/<int:id>', methods=['OPTIONS', 'POST'])
def new_employee(id):
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    encargado = Encargado.query.get(id)
    if not encargado:
        return jsonify({'error': 'Encargado no encontrado'}), 404


    data = request.get_json()
    if not data:
        return jsonify({'error': 'No se recibio datos'}), 400

    nombre = data.get('nombre')
    puesto = data.get('puesto')
    num_empleado = data.get('num_empleado')
    evaluador_id = data.get('evaluador_id')

    if not nombre or not puesto or not num_empleado:
        return jsonify({'error': 'Faltan datos'}), 400

    try:
        nuevo_empleado = Empleado(
            nombre=nombre,
            puesto=puesto,
            num_empleado=num_empleado,
            evaluador_id=evaluador_id
        )
        db.session.add(nuevo_empleado)
        db.session.commit()

        return jsonify({
            'message': 'Empleado creado correctamente',
            'empleado': {
                'id': nuevo_empleado.id,
                'nombre': nuevo_empleado.nombre,
                'puesto': nuevo_empleado.puesto,
                'num_empleado': nuevo_empleado.num_empleado,
                'evaluador': nuevo_empleado.evaluador_id
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error':'Error al crear el empleado', 'mensaje': str(e)}), 500

