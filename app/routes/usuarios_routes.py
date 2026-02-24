from flask import Blueprint, request, jsonify
from app.models import Usuario
from app import db

user_bp = Blueprint('user_bp', __name__)

# --------------- OBTENER TODOS LOS USUARIOS ----------------------------------------------------------
@user_bp.route('/usuarios', methods=['OPTIONS', 'GET'])
def obtener_todos_usuarios():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Obtener todos los usuarios
        usuarios = Usuario.query.all()
        
        if not usuarios:
            return jsonify({'message': 'No hay usuarios registrados'}), 404
        
        # Formatear la respuesta
        usuarios_data = []
        for usuario in usuarios:
            usuario_data = {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'usuario': usuario.usuario,
                'correo': usuario.correo,
                'rol_id': usuario.rol_id,
                'activo': usuario.activo
            }
            usuarios_data.append(usuario_data)
        
        return jsonify(usuarios_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --------------- CREAR NUEVO USUARIO ----------------------------------------------------------
@user_bp.route('/usuarios/nuevo', methods=['OPTIONS', 'POST'])
def crear_usuario():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data.get('nombre') or not data.get('usuario') or not data.get('password') or not data.get('rol_id'):
            return jsonify({'message': 'Faltan datos requeridos'}), 400
        
        # Verificar si ya existe un usuario con ese usuario
        usuario_existente = Usuario.query.filter_by (usuario=data['usuario']).first()
        if usuario_existente:
            return jsonify({'message': 'Ya existe un usuario con ese usuario'}), 409
        
        # Validar correo (opcional) y unicidad
        correo = (data.get('correo') or '').strip()
        if correo:
            correo_existente = Usuario.query.filter_by(correo=correo).first()
            if correo_existente:
                return jsonify({'message': 'Ya existe un usuario con ese correo'}), 409

        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            nombre=data['nombre'],
            usuario=data['usuario'],
            correo=correo if correo else None,
            contrasena=data['password'],  # Considera encriptar la contraseña
            rol_id=data['rol_id'],
            activo=True
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        return jsonify({
            'message': 'Usuario creado correctamente',
            'usuario': {
                'id': nuevo_usuario.id,
                'nombre': nuevo_usuario.nombre,
                'usuario': nuevo_usuario.usuario,
                'correo': nuevo_usuario.correo,
                'rol_id': nuevo_usuario.rol_id,
                'activo': nuevo_usuario.activo
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error al crear usuario: {str(e)}'}), 500

# --------------- ACTUALIZAR USUARIO ----------------------------------------------------------
@user_bp.route('/usuarios/<int:id>', methods=['OPTIONS', 'PUT'])
def actualizar_usuario(id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        # Buscar el usuario
        usuario = Usuario.query.get(id)
        if not usuario:
            return jsonify({'message': 'Usuario no encontrado'}), 404
        
        # Actualizar campos
        if 'nombre' in data:
            usuario.nombre = data['nombre']
        
        if  'usuario' in data:
            # Verificar si el usuario ya está en uso por otro usuario
            usuario_existente = Usuario.query.filter_by (usuario=data['usuario']).first()
            if usuario_existente and usuario_existente.id != id:
                return jsonify({'message': 'El usuario ya está en uso por otro usuario'}), 409
            usuario.usuario = data[ 'usuario']
        
        if 'password' in data and data['password']:
            usuario.contrasena = data['password']  # Considera encriptar la contraseña
        
        if 'rol_id' in data:
            usuario.rol_id = data['rol_id']
        
        if 'correo' in data:
            correo_new = (data['correo'] or '').strip()
            if correo_new:
                correo_existente = Usuario.query.filter_by(correo=correo_new).first()
                if correo_existente and correo_existente.id != id:
                    return jsonify({'message': 'El correo ya está en uso por otro usuario'}), 409
                usuario.correo = correo_new
            else:
                usuario.correo = None
        
        if 'activo' in data:
            usuario.activo = data['activo']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Usuario actualizado correctamente',
            'usuario': {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'usuario': usuario.usuario,
                'correo': usuario.correo,
                'rol_id': usuario.rol_id,
                'activo': usuario.activo
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error al actualizar usuario: {str(e)}'}), 500

# --------------- CAMBIAR ESTADO DE USUARIO (ACTIVAR/DESACTIVAR) ---------------------------
@user_bp.route('/usuarios/<int:id>/status', methods=['OPTIONS', 'PATCH'])
def cambiar_estado_usuario(id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        if 'activo' not in data:
            return jsonify({'error': 'Se requiere el campo "activo"'}), 400
        
        usuario = Usuario.query.get(id)
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Actualizar el estado del usuario
        usuario.activo = data['activo']
        db.session.commit()
        
        return jsonify({
            'message': f'Usuario {"activado" if usuario.activo else "desactivado"} correctamente',
            'usuario': {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'activo': usuario.activo
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500