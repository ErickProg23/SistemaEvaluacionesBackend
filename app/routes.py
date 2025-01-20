from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from .models import Usuario, Rol
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