from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app.models import Usuario, Encargado

# Definición del Blueprint para las rutas de login
login_bp = Blueprint('login_bp', __name__)

#LOGIN --------------------------------------------------------------------------------------------
@login_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    usuario = data.get('usuario')
    contrasena = data.get('contrasena')
    nombre = data.get('nombre')

    # Busca al usuario en la base de datos
    usuario = Usuario.query.filter_by(correo=correo).first()

    # Verificar si el usuario existe y la contraseña es correcta
    if contrasena and usuario and usuario.contrasena == contrasena:
        # Verificar si la cuenta está activa
        if not usuario.activo:
            return jsonify({'message': 'Cuenta desactivada. Contacte al administrador.'}), 403
            
        # Generar un token de acceso
        access_token = create_access_token(identity={'correo': usuario.correo})

        # Recupera el rol_id del usuario
        rol_id = usuario.rol_id  # Asegúrate de que `Usuario` tiene una columna llamada `rol_id`

        # Busca si el usuario tiene un registro en la tabla encargado
        encargado = Encargado.query.filter_by(usuario_id=usuario.id).first()

        # Si el encargado existe, obtenemos su ID y tipo_evaluacion, sino usamos null o un identificador especial
        id_encargado = encargado.id if encargado else None
        tipo_evaluacion = encargado.tipo_evaluacion if encargado else None
        
        # Guardar el ID del usuario en una variable separada
        usuario_id = usuario.id

        nombre = usuario.nombre
        
        return jsonify({'access_token': access_token}
        , {'rol_id': rol_id}
        , {'nombre': nombre},
        {'id_encargado': id_encargado},
        {'usuario_id': usuario_id},
        {'tipo_evaluacion': tipo_evaluacion}), 200

    return jsonify({'message': 'Correo o contraseña incorrectos'}), 401