from flask import Blueprint, request, jsonify
from app.models import Rol, db
from sqlalchemy.exc import IntegrityError

# Definición del Blueprint para las rutas de roles
roles_bp = Blueprint('roles_bp', __name__)

# OBTENER TODOS LOS ROLES
@roles_bp.route('/obtenerRoles', methods=['GET'])
def obtener_roles():
    """
    Obtiene todos los roles del sistema
    """
    try:
        roles = Rol.query.all()
        
        if roles:
            roles_data = []
            for rol in roles:
                rol_data = {
                    'id': rol.id,
                    'nombre': rol.nombre,
                    'descripcion': rol.descripcion
                }
                roles_data.append(rol_data)
            
            return jsonify(roles_data), 200
        else:
            return jsonify({'message': 'No se encontraron roles'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Error al obtener roles: {str(e)}'}), 500

# OBTENER ROL POR ID
@roles_bp.route('/obtener/<int:rol_id>', methods=['GET'])
def obtener_rol_por_id(rol_id):
    """
    Obtiene un rol específico por su ID
    """
    try:
        rol = Rol.query.get(rol_id)
        
        if rol:
            rol_data = {
                'id': rol.id,
                'nombre': rol.nombre,
                'descripcion': rol.descripcion
            }
            return jsonify(rol_data), 200
        else:
            return jsonify({'error': 'Rol no encontrado'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Error al obtener el rol: {str(e)}'}), 500

# CREAR NUEVO ROL
@roles_bp.route('/crearRol', methods=['POST'])
def crear_rol():
    """
    Crea un nuevo rol en el sistema
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
        
        nombre = data.get('nombre')
        descripcion = data.get('descripcion', '')
        
        if not nombre:
            return jsonify({'error': 'El nombre del rol es requerido'}), 400
        
        # Verificar si ya existe un rol con ese nombre
        rol_existente = Rol.query.filter_by(nombre=nombre).first()
        if rol_existente:
            return jsonify({'error': 'Ya existe un rol con ese nombre'}), 409
        
        # Crear nuevo rol
        nuevo_rol = Rol(
            nombre=nombre.strip(),
            descripcion=descripcion.strip() if descripcion else None
        )
        
        db.session.add(nuevo_rol)
        db.session.commit()
        
        return jsonify({
            'message': 'Rol creado correctamente',
            'rol': {
                'id': nuevo_rol.id,
                'nombre': nuevo_rol.nombre,
                'descripcion': nuevo_rol.descripcion
            }
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Error de integridad: El rol ya existe'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al crear el rol: {str(e)}'}), 500

# EDITAR ROL
@roles_bp.route('/editar/<int:rol_id>', methods=['PUT'])
def editar_rol(rol_id):
    """
    Edita un rol existente
    """
    try:
        # Verificar que la solicitud tenga contenido JSON
        if not request.is_json:
            return jsonify({'error': 'Se esperaba contenido JSON'}), 415
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
        
        # Buscar el rol
        rol = Rol.query.get(rol_id)
        if not rol:
            return jsonify({'error': 'Rol no encontrado'}), 404
        
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')
        
        if not nombre:
            return jsonify({'error': 'El nombre del rol es requerido'}), 400
        
        # Verificar si ya existe otro rol con ese nombre (excluyendo el actual)
        rol_existente = Rol.query.filter(
            Rol.nombre == nombre.strip(),
            Rol.id != rol_id
        ).first()
        
        if rol_existente:
            return jsonify({'error': 'Ya existe otro rol con ese nombre'}), 409
        
        # Actualizar los campos
        rol.nombre = nombre.strip()
        if descripcion is not None:
            rol.descripcion = descripcion.strip() if descripcion else None
        
        db.session.commit()
        
        return jsonify({
            'message': 'Rol actualizado correctamente',
            'rol': {
                'id': rol.id,
                'nombre': rol.nombre,
                'descripcion': rol.descripcion
            }
        }), 200
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Error de integridad: El nombre del rol ya existe'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar el rol: {str(e)}'}), 500

# ELIMINAR ROL (SOFT DELETE)
@roles_bp.route('/eliminar/<int:rol_id>', methods=['DELETE'])
def eliminar_rol(rol_id):
    """
    Elimina un rol del sistema (verificando que no esté en uso)
    """
    try:
        rol = Rol.query.get(rol_id)
        if not rol:
            return jsonify({'error': 'Rol no encontrado'}), 404
        
        # Verificar si el rol está siendo usado por usuarios
        from app.models import Usuario, Empleado, Encargado
        
        usuarios_con_rol = Usuario.query.filter_by(rol_id=rol_id).count()
        empleados_con_rol = Empleado.query.filter_by(rol_id=rol_id).count()
        encargados_con_rol = Encargado.query.filter_by(rol_id=rol_id).count()
        
        total_usos = usuarios_con_rol + empleados_con_rol + encargados_con_rol
        
        if total_usos > 0:
            return jsonify({
                'error': f'No se puede eliminar el rol porque está siendo usado por {total_usos} registro(s)',
                'detalles': {
                    'usuarios': usuarios_con_rol,
                    'empleados': empleados_con_rol,
                    'encargados': encargados_con_rol
                }
            }), 409
        
        # Si no está en uso, eliminar el rol
        db.session.delete(rol)
        db.session.commit()
        
        return jsonify({'message': 'Rol eliminado correctamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al eliminar el rol: {str(e)}'}), 500