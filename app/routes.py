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

@routes_blueprint.route('usuarios/empleados/<int:id>', methods=['OPTIONS', 'PUT'])
def deactivate_employee(id):    
    # Manejo del método PUT
    empleado = Empleado.query.get(id)
    if not empleado:
        return jsonify({'error': 'Empleado no encontrado'}), 404
    
    empleado.activo = False
    db.session.commit()
    return jsonify({'message': 'Empleado desactivado correctamente'})
