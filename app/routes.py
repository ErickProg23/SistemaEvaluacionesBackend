from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import create_access_token, jwt_required
from .models import Usuario, Rol, Empleado, Encargado, Pregunta, Evaluacion, Notificacion
from flask_cors import CORS
from app import db
from collections import defaultdict
from datetime import datetime, timedelta, date
from sqlalchemy import func, update
import pytz
from . import jwt, bcrypt  # Asegúrate de que `bcrypt` esté configurado en tu archivo principal


# Crear un Blueprint para las rutas
routes_blueprint = Blueprint('routes', __name__)

@jwt.user_identity_loader
def user_identity_lookup(user):
    return user  # Ajusta esto según el campo de identidad único de tu modelo de usuario


# --------------- OBTENER TODOS LOS USUARIOS ----------------------------------------------------------
@routes_blueprint.route('/usuarios', methods=['OPTIONS', 'GET'])
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
                'correo': usuario.correo,
                'rol_id': usuario.rol_id,
                'activo': usuario.activo
            }
            usuarios_data.append(usuario_data)
        
        return jsonify(usuarios_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --------------- CREAR NUEVO USUARIO ----------------------------------------------------------
@routes_blueprint.route('/usuarios/nuevo', methods=['OPTIONS', 'POST'])
def crear_usuario():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data.get('nombre') or not data.get('correo') or not data.get('password') or not data.get('rol_id'):
            return jsonify({'message': 'Faltan datos requeridos'}), 400
        
        # Verificar si ya existe un usuario con ese correo
        usuario_existente = Usuario.query.filter_by(correo=data['correo']).first()
        if usuario_existente:
            return jsonify({'message': 'Ya existe un usuario con ese correo'}), 409
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            nombre=data['nombre'],
            correo=data['correo'],
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
                'correo': nuevo_usuario.correo,
                'rol_id': nuevo_usuario.rol_id,
                'activo': nuevo_usuario.activo
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error al crear usuario: {str(e)}'}), 500

# --------------- ACTUALIZAR USUARIO ----------------------------------------------------------
@routes_blueprint.route('/usuarios/<int:id>', methods=['OPTIONS', 'PUT'])
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
        
        if 'correo' in data:
            # Verificar si el correo ya está en uso por otro usuario
            usuario_existente = Usuario.query.filter_by(correo=data['correo']).first()
            if usuario_existente and usuario_existente.id != id:
                return jsonify({'message': 'El correo ya está en uso por otro usuario'}), 409
            usuario.correo = data['correo']
        
        if 'password' in data and data['password']:
            usuario.contrasena = data['password']  # Considera encriptar la contraseña
        
        if 'rol_id' in data:
            usuario.rol_id = data['rol_id']
        
        if 'activo' in data:
            usuario.activo = data['activo']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Usuario actualizado correctamente',
            'usuario': {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'correo': usuario.correo,
                'rol_id': usuario.rol_id,
                'activo': usuario.activo
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error al actualizar usuario: {str(e)}'}), 500

# --------------- CAMBIAR ESTADO DE USUARIO (ACTIVAR/DESACTIVAR) ---------------------------
@routes_blueprint.route('/usuarios/<int:id>/status', methods=['OPTIONS', 'PATCH'])
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

#LOGIN --------------------------------------------------------------------------------------------
@routes_blueprint.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    correo = data.get('correo')
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


#OBTENER DATOS --------------------------------------------------------------------------------------------

@routes_blueprint.route('/usuarios/empleados', methods=['GET'])
def get_empleados():
    empleados = Empleado.query.filter_by(rol_id=3).all()

    if empleados:
        empleados_data = []
        for empleado in empleados:
            
            # Mapear los nombres de los encargados asociados
            encargados_nombres = [encargado.nombre for encargado in empleado.encargados]

            empleados_data.append({
                'id': empleado.id,
                'nombre': empleado.nombre,
                'puesto': empleado.puesto,
                'num_empleado': empleado.num_empleado,
                'tipo_evaluacion': empleado.tipo_evaluacion,
                'activo': empleado.activo,
                'encargados': encargados_nombres
            })
        return jsonify(empleados_data), 200

    return jsonify({'message': 'No se pudo extraer la información'}), 401


@routes_blueprint.route('/usuarios/encargados', methods=['GET'])
def get_encargados():
    encargados = Encargado.query.all()

    if encargados:
        encargados_data = []
        
        for encargado in encargados:
            # Ahora usamos la relación con la tabla intermedia para contar empleados asignados
            num_empleados = len(encargado.empleados)  # Usamos la relación 'empleados' en vez de 'evaluador_id'
            
            encargado_data = {
                'id': encargado.id,
                'nombre': encargado.nombre,
                'activo': encargado.activo,
                'puesto': encargado.puesto,
                'num_empleado': encargado.num_empleado,
                'num_empleados_asignados': num_empleados  # Número de empleados asignados
            }
            encargados_data.append(encargado_data)   
        return jsonify(encargados_data), 200
    else:
        return jsonify({'message': 'No se encontraron encargados'}), 404

@routes_blueprint.route('/usuarios/empleados/<int:encargado_id>', methods=['GET'])
def obtener_empleados_por_encargado(encargado_id):
    try:
        # Consultar empleados asociados al encargado específico
        empleados = Empleado.query.filter(Empleado.encargados.any(id=encargado_id)).all()

        if not empleados:
            return jsonify([]), 200

        # Crear la lista de empleados
        empleados_data = [
            {
                'id': empleado.id,
                'nombre': empleado.nombre,
                'puesto': empleado.puesto,
                'num_empleado': empleado.num_empleado,
                'tipo_evaluacion': empleado.tipo_evaluacion,
                'activo': empleado.activo
            }
            for empleado in empleados
        ]

        return jsonify(empleados_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routes_blueprint.route('/usuarios/empleados-por-usuario/<int:usuario_id>', methods=['GET'])
def obtener_empleados_por_usuario_superior(usuario_id):
    try:
        # 1. Obtenemos los encargados activos asociados a este usuario superior
        encargados = Encargado.query.filter(
            Encargado.encargados.any(id=usuario_id),
            Encargado.activo == True
        ).all()
        
        if not encargados:
            return jsonify([]), 200
        
        # 2. Crear la lista de encargados activos
        encargados_data = [
            {
                'id': encargado.id,
                'nombre': encargado.nombre,
                'puesto': encargado.puesto,
                'num_empleado': encargado.num_empleado,
                'activo': encargado.activo,
                'num_empleados_asignados': len(encargado.empleados)  # Número de empleados asignados
            }
            for encargado in encargados
        ]
        
        return jsonify(encargados_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_blueprint.route('/usuarios/mayores', methods=['GET'])
def get_mayores():
    usuarios = Usuario.query.filter_by(rol_id=4).all()

    if usuarios:
        usuarios_data = [{'id': usuario.id, 'nombre': usuario.nombre, 'activo': usuario.activo} 
        for usuario in  usuarios]
        return jsonify(usuarios_data), 200
    else:
        return jsonify({'message': 'No se pudo extraer la informacion'}), 401


        
@routes_blueprint.route('/usuarios/empleado/<int:id>', methods=['GET'])
def obtener_empleado(id):
    # Obtiene al empleado junto con sus encargados
    empleado = Empleado.query.filter_by(id=id).first()

    if empleado:
        # Construcción del resultado con la información de los encargados
        empleados_encargados = []
        for encargado in empleado.encargados:
            empleados_encargados.append({
                'id': encargado.id,
                'nombre': encargado.nombre
            })
        
        empleado_data = {
            'id': empleado.id,
            'nombre': empleado.nombre,
            'puesto': empleado.puesto,
            'num_empleado': empleado.num_empleado,
            'tipo_evaluacion': empleado.tipo_evaluacion,
            'activo': empleado.activo,
            'encargados': empleados_encargados  # Ahora es una lista de encargados
        }

        return jsonify(empleado_data), 200
    else:
        return jsonify({'message': 'No se pudo extraer la información'}), 404


@routes_blueprint.route('/usuarios/encargado/<int:id>', methods=['GET'])
def obtener_encargado(id):
    # Obtiene al empleado con su evaluador
    encargado = Encargado.query.filter_by(id=id).first()

    if encargado:
        # Construcción del resultado con la información del evaluador
        encargados_usuarios = []
        for usuario in encargado.encargados:
            encargados_usuarios.append({
                'id': usuario.id,
                'nombre': usuario.nombre
            })

    if encargado:
        # Construcción del resultado con la información del evaluador
        encargado_data = {
            'id': encargado.id,
            'nombre': encargado.nombre,
            'puesto': encargado.puesto,
            'num_empleado': encargado.num_empleado,
            'activo': encargado.activo,
            'encargados': encargados_usuarios
        }
        return jsonify(encargado_data), 200
    else:
        return jsonify({'message': 'No se pudo extraer la información'}), 404

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

@routes_blueprint.route('/preguntas/evaluacion', methods=['GET'])
def obtener_preguntas():
     # Obtener el tipo desde los parámetros de la URL
    tipo = request.args.get('tipo')

    if not tipo:
        return jsonify({"mensaje": "El parámetro 'tipo' es requerido"}), 400

    try:
        tipo = int(tipo)
    except ValueError:
        return jsonify({"mensaje": "El tipo debe ser un número entero"}), 400

    # Buscar preguntas del tipo solicitado O tipo 3
    preguntas = Pregunta.query.filter(
        (Pregunta.tipo == tipo) | (Pregunta.tipo == 3)
    ).all()

    if not preguntas:
        return jsonify({"mensaje": "No hay preguntas disponibles"}), 404

    preguntas_json = [pregunta.to_dict() for pregunta in preguntas]
    return jsonify(preguntas_json), 200

@routes_blueprint.route('/preguntas', methods=['GET'])
def obtener_Todaspreguntas():
    # Obtener todas las preguntas sin filtrar por tipo
    preguntas = Pregunta.query.all()

    if not preguntas:
        return jsonify({"mensaje": "No hay preguntas disponibles"}), 404

    preguntas_json = [pregunta.to_dict() for pregunta in preguntas]
    return jsonify(preguntas_json), 200


# Crear nueva pregunta
@routes_blueprint.route('/newPregunta', methods=['OPTIONS', 'POST'])
def crear_pregunta():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Verificar que la solicitud es JSON
        if not request.is_json:
            return jsonify({'error': 'Se esperaba un contenido JSON'}), 415
        
        # Obtener datos de la solicitud
        data = request.json
        
        # Validar datos requeridos
        if 'texto' not in data or 'tipo' not in data:
            return jsonify({'error': 'Faltan campos requeridos (texto, tipo)'}), 400
        
        # Crear nueva pregunta
        nueva_pregunta = Pregunta(
            texto=data['texto'],
            tipo=data['tipo'],
            peso=data['peso'],
            descripcion=data['descripcion'],
            estado=data.get('estado', 1)  # Por defecto activo
        )
        
        # Guardar en la base de datos
        db.session.add(nueva_pregunta)
        db.session.commit()
        
        # Devolver la pregunta creada con su ID
        return jsonify(nueva_pregunta.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Editar pregunta existente
@routes_blueprint.route('/preguntas/<int:id>', methods=['OPTIONS', 'PUT'])
def editar_pregunta(id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Verificar que la solicitud es JSON
        if not request.is_json:
            return jsonify({'error': 'Se esperaba un contenido JSON'}), 415
        
        # Buscar la pregunta
        pregunta = Pregunta.query.get(id)
        if not pregunta:
            return jsonify({'error': 'Pregunta no encontrada'}), 404
        
        # Obtener datos de la solicitud
        data = request.json
        
        # Actualizar campos
        if 'texto' in data:
            pregunta.texto = data['texto']
        
        if 'tipo' in data:
            pregunta.tipo = data['tipo']
        
        if 'estado' in data:
            pregunta.estado = data['estado']

        if 'peso' in data:
            pregunta.peso = data['peso']

        if 'descripcion' in data:
            pregunta.descripcion = data['descripcion']

        
        
        # Guardar cambios
        db.session.commit()
        
        # Devolver la pregunta actualizada
        return jsonify(pregunta.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ACTUALIZAR DATOS --------------------------------------------------------------------------------------------

@routes_blueprint.route('/usuarios/empleados/desactivar/<int:id>', methods=['OPTIONS', 'PUT'])
def deactivate_employee(id):    
    # Manejo del método PUT
    empleado = Empleado.query.get(id)
    if not empleado:
        return jsonify({'error': 'Empleado no encontrado'}), 404
    
    empleado.activo = False
    db.session.commit()
    return jsonify({'message': 'Empleado desactivado correctamente'})

@routes_blueprint.route('/usuarios/encargados/desactivar/<int:id>', methods=['OPTIONS', 'PUT'])
def deactivate_encargado(id):    
    # Manejo del método PUT
    encargado = Encargado.query.get(id)
    if not encargado:
        return jsonify({'error': 'Encargado no encontrado'}), 404
    
    encargado.activo = False
    db.session.commit()
    return jsonify({'message': 'Encargado desactivado correctamente'})

@routes_blueprint.route('/usuarios/encargados/activar/<int:id>', methods=['OPTIONS', 'PUT'])
def activate_encargado(id):    
    # Manejo del método PUT
    encargado = Encargado.query.get(id)
    if not encargado:
        return jsonify({'error': 'Encargado no encontrado'}), 404
    
    encargado.activo = True
    db.session.commit()
    return jsonify({'message': 'Encargado activado correctamente'})


@routes_blueprint.route('/usuarios/empleados/activar/<int:id>', methods=['OPTIONS', 'PUT'])
def activate_empleado(id):    
    # Manejo del método PUT
    empleado = Empleado.query.get(id)
    if not empleado:
        return jsonify({'error': 'Empledado no encontrado'}), 404
    
    empleado.activo = True
    db.session.commit()
    return jsonify({'message': 'Empleado activado correctamente'})

@routes_blueprint.route('/empleado/editar/<int:id>', methods =['PUT'])
def editar_empleado(id):
    # Manejo del método PUT
      # Asegúrate de que la solicitud tiene el tipo de contenido correcto
    if request.content_type != 'application/json':
        return jsonify({'error': 'Tipo de contenido no soportado, se esperaba application/json'}), 415
    
    empleado = Empleado.query.get(id)

    if not empleado:
        return jsonify({'error': 'Empleado no encontrado'}), 404

    # Manejo de la solicitud
    data = request.json
    empleado.nombre = data['nombre']
    empleado.puesto = data['puesto']
    empleado.num_empleado = data['num_empleado']
    empleado.tipo_evaluacion = data['tipo_evaluacion']

    db.session.commit()

    # Si 'encargados_ids' está en la solicitud
    if 'encargados_ids' in data:
        nuevos_encargados_ids = set(data['encargados_ids'])
        encargados_actuales_ids = set(encargado.id for encargado in empleado.encargados)

        # Encargados a eliminar (los que están asignados pero no están en los nuevos ids)
        encargados_a_eliminar = encargados_actuales_ids - nuevos_encargados_ids
        for encargado in empleado.encargados:
            if encargado.id in encargados_a_eliminar:
                empleado.encargados.remove(encargado)

        # Encargados a agregar (los que no están ya asignados)
        encargados_a_agregar = nuevos_encargados_ids - encargados_actuales_ids
        encargados = Encargado.query.filter(Encargado.id.in_(encargados_a_agregar)).all()

        # Verificar que todos los encargados existen
        if len(encargados) != len(encargados_a_agregar):
            return jsonify({'error': 'Uno o más encargados no fueron encontrados'}), 404

        # Asignar los encargados al empleado
        for encargado in encargados:
            empleado.encargados.append(encargado)

    db.session.commit()

    return jsonify({'message': 'Empleado editado correctamente'}), 200


@routes_blueprint.route('/encargado/editar/<int:id>', methods =['PUT'])
def editar_encargado(id):
    # Manejo del método PUT
      # Asegúrate de que la solicitud tiene el tipo de contenido correcto
    if not request.is_json:
        return jsonify({'error': 'Se esperaba un contenido JSON'}), 415


    encargado = Encargado.query.get(id)

    if not encargado:
        return jsonify({'error': 'Empleado no encontrado'}), 404

    # Manejo de la solicitud
    data = request.json
    encargado.nombre = data.get('nombre', encargado.nombre)
    encargado.puesto = data.get('puesto', encargado.puesto)
    encargado.num_empleado = data.get('num_empleado', encargado.num_empleado)

    # Si 'encargados_ids' está en la solicitud
    if 'encargados_ids' in data:
        nuevos_encargados_ids = set(data['encargados_ids'])
        encargados_actuales_ids = set(usuario.id for usuario in encargado.encargados)

        # Encargados a eliminar (los que están asignados pero no están en los nuevos ids)
        encargados_a_eliminar = encargados_actuales_ids - nuevos_encargados_ids
        for usuario in encargado.encargados:
            if usuario.id in encargados_a_eliminar:
                encargado.encargados.remove(usuario)

        # Encargados a agregar (los que no están ya asignados)
        encargados_a_agregar = nuevos_encargados_ids - encargados_actuales_ids
        encargados = Usuario.query.filter(Usuario.id.in_(encargados_a_agregar)).all()

        # Verificar que todos los encargados existen
        if len(encargados) != len(encargados_a_agregar):
            return jsonify({'error': 'Uno o más encargados no fueron encontrados'}), 404

        # Asignar los encargados al empleado
        for usuario in encargados:
            encargado.encargados.append(usuario)

    try:
        db.session.commit()
        return jsonify({'message': 'Encargado editado correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# CREACION NUEVO EMPLEADO Y ENCARGADO --------------------------------------------------------------------------------------------

@routes_blueprint.route('/empleados/nuevo', methods=['OPTIONS', 'POST'])
def new_employee():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No se recibio datos'}), 400

    nombre = data.get('nombre').strip().lower()  # Convertir a minúsculas y quitar espacios
    puesto = data.get('puesto')
    num_empleado = data.get('num_empleado')
    encargados_ids = data.get('encargados_ids', [])

    if not encargados_ids:
        tipo_evaluacion = 0
    # Determinar tipo_evaluacion basado en encargados_ids
    elif len(encargados_ids) >= 2:
        # Si hay 2 o más encargados, asignar tipo_evaluacion = 3
        tipo_evaluacion = 3
    elif len(encargados_ids) == 1:
        # Si hay solo 1 encargado, buscar su tipo_evaluacion
        encargado = Encargado.query.get(encargados_ids[0])
        if encargado:
            tipo_evaluacion = encargado.tipo_evaluacion
        else:
            tipo_evaluacion = 1

    if not nombre or not puesto or not num_empleado:
        return jsonify({'error': 'Faltan datos'}), 400

    try:

        nuevo_empleado = Empleado(
            nombre=nombre,
            puesto=puesto,
            num_empleado=num_empleado,
            rol_id=3,  # ID para empleado
            tipo_evaluacion=tipo_evaluacion,
            activo=True
        )
        db.session.add(nuevo_empleado)
        db.session.flush()

        # Relacionar los encargados seleccionados con el empleado
        if encargados_ids:
            encargados = Encargado.query.filter(Encargado.id.in_(encargados_ids)).all()
            if len(encargados) != len(encargados_ids):
                return jsonify({'error': 'Uno o más encargados no encontrados'}), 404

            nuevo_empleado.encargados.extend(encargados)  # Asignar la relación muchos a muchos

        db.session.commit()

        return jsonify({
            'message': 'Empleado creado correctamente',
            'empleado': {
                'id': nuevo_empleado.id,
                'nombre': nuevo_empleado.nombre,
                'puesto': nuevo_empleado.puesto,
                'encargados': [{'id': e.id, 'nombre': e.nombre} for e in nuevo_empleado.encargados],  # Mostrar los encargados
                'num_empleado': nuevo_empleado.num_empleado,
                'tipo_evaluacion': nuevo_empleado.tipo_evaluacion,
                'rol': nuevo_empleado.rol_id
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al crear el empleado', 'mensaje': str(e)}), 500


@routes_blueprint.route('/encargados/nuevo', methods=['OPTIONS', 'POST'])
def nuevo_encargado():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No se recibio datos'}), 400

    # Guardar el nombre original
    nombre_original = data.get('nombre')
    
    # Usar una versión modificada del nombre para la búsqueda
    nombre_busqueda = nombre_original.strip().lower() if nombre_original else ""
    
    puesto = data.get('puesto')
    num_empleado = data.get('num_empleado')
    encargados_ids = data.get('encargados_ids', [])
    tipo_evaluacion = data.get('tipo_evaluacion')
    rol_id = data.get('rol_id',2)
    
    if not nombre_original or not puesto or not num_empleado:
        return jsonify({'error': 'Faltan datos'}), 400

    try:
        # Paso 1: Buscar el usuario por nombre (usando la versión modificada para búsqueda)
        usuario = Usuario.query.filter(Usuario.nombre.collate('utf8mb4_general_ci') == nombre_busqueda).first()
        if not usuario:
            return jsonify({'error': f'No existe un usuario con el nombre "{nombre_original}"'}), 404

        nuevo_encargado = Encargado(
            nombre=nombre_original,  # Usar el nombre original para guardar
            puesto=puesto,
            num_empleado=num_empleado,
            tipo_evaluacion=tipo_evaluacion,
            rol_id=rol_id,
            usuario_id=usuario.id
        )
        db.session.add(nuevo_encargado)
        db.session.flush()

        # Relacionar los encargados seleccionados con el empleado
        if encargados_ids:
            encargados = Usuario.query.filter(Usuario.id.in_(encargados_ids)).all()
            if len(encargados) != len(encargados_ids):
                return jsonify({'error': 'Uno o más encargados no encontrados'}), 404

            nuevo_encargado.encargados.extend(encargados)  # Asignar la relación muchos a muchos

        db.session.commit()

        return jsonify({
            'message': 'Encargado creado correctamente',
            'encargado': {
                'id': nuevo_encargado.id,
                'nombre': nuevo_encargado.nombre,
                'usuario_id': nuevo_encargado.usuario_id,
                'puesto': nuevo_encargado.puesto,
                'encargados': [{'id': e.id, 'nombre': e.nombre} for e in nuevo_encargado.encargados],  # Mostrar los evaluadores
                'num_empleado': nuevo_encargado.num_empleado,
                'rol': nuevo_encargado.rol_id
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al crear el encargado', 'mensaje': str(e)}), 500



# PROMOVER EMPLEADOS ---------------------------------------------------------------------------------------------  
@routes_blueprint.route('/empleados/promover/<int:id>', methods=['OPTIONS', 'POST'])
def promote_employee(id):
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    # Obtener el empleado por ID
    empleado = Empleado.query.get(id)
    if not empleado:
        return jsonify({'error': 'Empleado no encontrado'}), 404

    try:
        # Cambiar el rol del empleado a 2
        empleado.rol_id = 2

         # Mover el empleado a la tabla de Encargado
        encargado = Encargado(
            nombre=empleado.nombre,
            puesto=empleado.puesto,
            num_empleado=empleado.num_empleado,
            rol_id=empleado.rol_id,
            activo=True,
            evaluador_id=4,
            fecha_creacion=datetime.utcnow()  # Agregar la fecha de promoción
        )

        # Agregar el empleado a la tabla de encargados
        db.session.add(encargado)

        # Eliminar el empleado de la tabla original si es necesario
        # db.session.delete(empleado)  # Descomenta esta línea si quieres eliminarlo de la tabla original

        db.session.commit()

        return jsonify({
            'message': 'Empleado promovido correctamente',
            'empleado': {
                'id': empleado.id,
                'nombre': empleado.nombre,
                'puesto': empleado.puesto,
                'num_empleado': empleado.num_empleado,
                'rol_id': empleado.rol_id,
                'activo': empleado.activo,
                'evaluador_id': empleado.evaluador_id # Confirmamos el nuevo rol
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al promover el empleado', 'mensaje': str(e)}), 500



# GUARDAR EVALUACION  -------------------------------------------------------------------------------------------------------
@routes_blueprint.route('/evaluacion/nueva', methods=['OPTIONS', 'POST'])
def guardar_evaluacion():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    try:
        data = request.json
        payload = data.get('payload')
        id_encargado = data.get('idEncargado')
        num_semana = data.get('num_semana')
        tipo_evaluacion = data.get('tipo_evaluacion')

        if not payload or not id_encargado:
            return jsonify({'error': 'Datos incompletos'}), 400

        for evaluacion_data in payload:
            empleado_id = evaluacion_data.get('empleado_id')
            calificaciones = evaluacion_data.get('calificaciones')
            comentarios = evaluacion_data.get('comentarios')
            ausente = evaluacion_data.get('ausente', False)

            if isinstance(comentarios, list):
                comentarios = ', '.join(comentarios)

            ausente_db = 1 if ausente else 0

            for aspecto_texto, calificacion in calificaciones.items():
                # Buscar el aspecto en la base de datos por nombre
                aspecto_db = Pregunta.query.filter_by(texto=aspecto_texto).first()

                if aspecto_db:
                    peso = aspecto_db.peso

                porcentaje = calificacion * peso

                nueva_evaluacion = Evaluacion(
                    empleado_id=empleado_id,
                    encargado_id=id_encargado,
                    fecha_evaluacion=datetime.now(),
                    aspecto=aspecto_texto,
                    total_puntos=calificacion,
                    porcentaje_total=porcentaje,
                    comentarios=comentarios,
                    ausente=ausente_db,
                    num_semana=num_semana,
                    tipo_evaluacion=tipo_evaluacion
                )
                db.session.add(nueva_evaluacion)

        db.session.commit()
        return jsonify({'message': 'Evaluaciones guardadas correctamente'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


#----------------------------NOTIFICACIONES------------------------------------------------------
@routes_blueprint.route('/notificaciones/nueva', methods=['OPTIONS', 'POST'])
def nueva_notificacion():
    # Obtener el payload de la solicitud

     # 1. Verificar el tipo de solicitud
    if request.method == 'OPTIONS':
        return '', 200  # Si es un preflight request para CORS

    try:
        data = request.get_json()

        id_encargado = data['id_encargado']
        id_empleado = data['id_empleado']
        accion = data['accion']
        activo = data['activo']


        fecha_actual = datetime.now()

        if isinstance(id_encargado, list):
            for encargado_id in id_encargado:
                nueva_notificacion = Notificacion(
                    id_encargado=encargado_id,
                    id_empleado=id_empleado,
                    accion=accion,
                    fecha=fecha_actual
                )
                db.session.add(nueva_notificacion)

        else: 
            nueva_notificacion = Notificacion(
                id_encargado=id_encargado,
                id_empleado=id_empleado,
                accion=accion,
                fecha=fecha_actual
            )
            db.session.add(nueva_notificacion)

        db.session.commit()

        return jsonify({'message': 'Notificación creada correctamente'}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error al crear la notificacion: {e}")
        return jsonify({'error': str(e)}), 500

# -------------------------------ELIMINAR NOTIFICACIONES-------------------------------------
@routes_blueprint.route('/notificaciones/eliminar', methods=['OPTIONS', 'POST'])
def eliminar_notificacion():

    # 1. Verificar el tipo de solicitud
    if request.method == 'OPTIONS':
        return '', 200  # Si es un preflight request para CORS

    try:
        data = request.get_json()

        if not data or 'id' not in data:
            return jsonify({'error': 'Falta el id de la notificación'}), 400

        notificacion_id = data['id']

        notificacion = Notificacion.query.get(notificacion_id)

        if not notificacion:
            return jsonify({'error': 'Notificación no encontrada'}), 404

        notificacion.activo = False

        db.session.commit()

        return jsonify({'message': 'Notificación eliminada correctamente'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar la notificacion: {e}")
        return jsonify({'error': str(e)}), 500

    


# --------------- OBTENER NOTIFICACIONES ----------------------------------------------------------
@routes_blueprint.route('/notificaciones', methods=['OPTIONS', 'GET'])
def obtener_notificaciones():

    encargado_id = request.args.get('encargado_id', type=int)
    if not encargado_id:
        return jsonify({'error': 'Falta el parámetro encargado_id'}), 400

    fecha_limite = datetime.utcnow() - timedelta(days=60) # 60 dias atras desde hoy

    notificaciones = Notificacion.query.filter(
        Notificacion.id_encargado == encargado_id,
        Notificacion.fecha >= fecha_limite
    ).all()

    if not notificaciones:
        return jsonify({'message': 'No hay notificaciones'}), 404

    notificaciones_data = []
    for notificacion in notificaciones:
        notificaciones_data.append({
            'id': notificacion.id,
            'activo': notificacion.activo,
            'id_encargado': notificacion.id_encargado,
            'id_empleado': notificacion.id_empleado,
            'accion': notificacion.accion,
            'fecha': notificacion.fecha.strftime('%Y-%m-%d %H:%M:%S')
        })

    return jsonify({'notificaciones': notificaciones_data}), 200

# --------------- ELIMINACION DE NOTIFICACIONES TODAS ----------------------------------------------------------
@routes_blueprint.route('/notificaciones/eliminar-todas', methods=['OPTIONS','POST'])
def eliminar_todas_notificaciones():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        ids = data.get('ids', [])

        if not ids:
            return jsonify({'error': 'Se requieren IDs de notificaciones'}), 400

        # Desactivar solo las notificaciones con IDs recibidos y activas
        stmt = update(Notificacion).where(
            Notificacion.id.in_(ids),
            Notificacion.activo == True
        ).values(activo=False)

        result = db.session.execute(stmt)
        db.session.commit()

        return jsonify({
            "message": f"{result.rowcount} notificaciones desactivadas",
            "ids": ids
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error desactivando notificaciones: {str(e)}")
        return jsonify({"error": "Error al desactivar notificaciones"}), 500





# --------------- OBTENCION DE EVALUACIONES ----------------------------------------------------------
@routes_blueprint.route('/evaluaciones/todas', methods=['OPTIONS', 'GET'])
def obtener_evaluaciones_todas():
    try:
        from collections import defaultdict

        # Obtener todas las evaluaciones válidas (no ausentes)
        evaluaciones = Evaluacion.query.filter(Evaluacion.ausente == 0).all()

        if not evaluaciones:
            return jsonify({'error': 'No hay evaluaciones'}), 404

        # IDs únicos de empleados evaluados
        empleado_ids = {eval.empleado_id for eval in evaluaciones}

        # Obtener datos de empleados
        empleados = db.session.query(
            Empleado.id, Empleado.nombre, Empleado.tipo_evaluacion
        ).filter(Empleado.id.in_(empleado_ids)).all()

        empleados_dict = {
            emp.id: {
                'nombre': emp.nombre,
                'tipo_evaluacion': emp.tipo_evaluacion
            } for emp in empleados
        }

        aspectos_por_tipo = {
            1: 9,  # operativo
            2: 8   # administrativo
        }

        # Agrupar evaluaciones
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            evaluaciones_agrupadas[eval.empleado_id][eval.encargado_id][fecha_str].append(eval)

        resultados = defaultdict(lambda: {
            'suma_porcentaje_total': 0.0,
            'total_evaluaciones_completas': 0,
            'nombre': 'Nombre no encontrado',
            'tipo_evaluacion': 1
        })

        for empleado_id, encargados in evaluaciones_agrupadas.items():
            empleado_info = empleados_dict.get(empleado_id, {})
            tipo = empleado_info.get('tipo_evaluacion', 1)
            aspectos_esperados = aspectos_por_tipo.get(tipo, 9)

            for encargado_id, fechas in encargados.items():
                for fecha, evals in fechas.items():
                    if len(evals) == aspectos_esperados:
                        resultados[empleado_id]['total_evaluaciones_completas'] += 1
                        suma = sum(float(eval.porcentaje_total) for eval in evals)
                        resultados[empleado_id]['suma_porcentaje_total'] += suma
                        resultados[empleado_id]['nombre'] = empleado_info.get('nombre', 'Nombre no encontrado')
                        resultados[empleado_id]['tipo_evaluacion'] = tipo

        # Calcular porcentaje final (base fija de 500 por evaluación)
        for empleado_id, datos in resultados.items():
            total = datos['total_evaluaciones_completas']
            if total > 0:
                porcentaje_final = (datos['suma_porcentaje_total'] / (500 * total)) * 100
                datos['porcentaje_final'] = min(porcentaje_final, 100.0)
            else:
                datos['porcentaje_final'] = 0.0

        # Calcular promedio general
        promedios = [datos['porcentaje_final'] for datos in resultados.values() if datos['total_evaluaciones_completas'] > 0]
        promedio_general = sum(promedios) / len(promedios) if promedios else 0

        return jsonify({
            'promedio_general': round(promedio_general, 2),
            'total_empleados': len(promedios),
            'detalle_empleados': [
                {
                    'nombre': datos['nombre'],
                    'empleado_id': emp_id,
                    'calificacion_final': round(datos['porcentaje_final'], 2),
                    'total_evaluaciones': datos['total_evaluaciones_completas']
                } for emp_id, datos in resultados.items() if datos['total_evaluaciones_completas'] > 0
            ]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --------------- OBTENCION DE EVALUACIONES CON ENCARGADOS ----------------------------------------------------------
@routes_blueprint.route('/evaluaciones/todas-de-encargados', methods=['OPTIONS','GET'])
def obtener_evaluaciones_todas_con_encargados():
    if request.method == 'OPTIONS':
        return '', 200
        
    try: 
        # Obtener parámetros de filtro
        encargado_id = request.args.get('encargado_id', type=int)
        periodo_tipo = request.args.get('periodo_tipo', 'month')
        periodo_valor = request.args.get('periodo_valor')
        
        # Construir la consulta base
        query = Evaluacion.query
        
        # Aplicar filtro de encargado si se proporciona
        if encargado_id:
            query = query.filter(Evaluacion.encargado_id == encargado_id)
        
        # Aplicar filtros según el tipo de periodo
        if periodo_tipo and periodo_valor:
            # Mapear periodo a español
            periodo_mapeado = {
                'month': 'mes',
                'year': 'año',
                'week': 'semana',
                'mes': 'mes',  # Compatibilidad con español
                'año': 'año',
                'semana': 'semana'
            }.get(periodo_tipo.lower(), None)
            
            if periodo_mapeado == 'semana':
                # Para semanas, filtrar directamente por el campo num_semana
                try:
                    num_semana = int(periodo_valor)
                    if num_semana < 1 or num_semana > 53:
                        return jsonify({'error': 'Número de semana inválido (debe estar entre 1 y 53)'}), 400
                    
                    query = query.filter(Evaluacion.num_semana == num_semana)
                except ValueError:
                    return jsonify({'error': 'Formato de semana inválido. Use un número entre 1 y 53.'}), 400
            
            elif periodo_mapeado == 'mes':
                # Si el valor es solo el mes (ej: "05" o "4")
                current_year = datetime.now().year
                try:
                    if periodo_valor.isdigit() and '-' not in periodo_valor:
                        month = int(periodo_valor)
                        if month < 1 or month > 12:
                            return jsonify({'error': 'Mes inválido (debe estar entre 1 y 12)'}), 400
                        
                        fecha_inicio = date(current_year, month, 1)
                        if month == 12:
                            fecha_fin = date(current_year + 1, 1, 1) - timedelta(days=1)
                        else:
                            fecha_fin = date(current_year, month + 1, 1) - timedelta(days=1)
                    else:
                        # Si en algún caso envía "YYYY-MM"
                        year, month = map(int, periodo_valor.split('-'))
                        fecha_inicio = date(year, month, 1)
                        if month == 12:
                            fecha_fin = date(year + 1, 1, 1) - timedelta(days=1)
                        else:
                            fecha_fin = date(year, month + 1, 1) - timedelta(days=1)
                    
                    query = query.filter(
                        Evaluacion.fecha_evaluacion >= fecha_inicio,
                        Evaluacion.fecha_evaluacion <= fecha_fin
                    )
                except ValueError:
                    return jsonify({'error': 'Formato de mes inválido. Use MM o YYYY-MM'}), 400
            
            elif periodo_mapeado == 'año':
                # El valor es el año (ej: "2023")
                try:
                    year = int(periodo_valor)
                    if year < 2000 or year > 2100:
                        return jsonify({'error': 'Año inválido (2000-2100)'}), 400
                    
                    fecha_inicio = date(year, 1, 1)
                    fecha_fin = date(year, 12, 31)
                    
                    query = query.filter(
                        Evaluacion.fecha_evaluacion >= fecha_inicio,
                        Evaluacion.fecha_evaluacion <= fecha_fin
                    )
                except ValueError:
                    return jsonify({'error': 'Formato de año inválido. Use YYYY'}), 400
        
        # Ejecutar la consulta
        evaluaciones = query.all()
        
        if not evaluaciones:
            return jsonify({'message': 'No hay evaluaciones para los filtros seleccionados'}), 404

        # Obtener IDs de empleados únicos
        empleado_ids = {eval.empleado_id for eval in evaluaciones}
        
        # Consultar nombres de empleados
        empleados = db.session.query(Empleado.id, Empleado.nombre).filter(
            Empleado.id.in_(empleado_ids)
        ).all()
        empleados_dict = {emp.id: emp.nombre for emp in empleados}
        
        # Agrupar evaluaciones por empleado y fecha
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            empleado_id = eval.empleado_id
            evaluaciones_agrupadas[empleado_id][fecha_str].append(eval)
        
        # Procesar datos por empleado
        resultados_empleados = defaultdict(lambda: {
            'suma_porcentaje_total': 0.0,
            'total_evaluaciones_completas': 0,
            'nombre': 'Nombre no encontrado',
            'tiene_ausencia': False
        })
        
        # Inicializar datos para todos los empleados
        for empleado_id in empleado_ids:
            resultados_empleados[empleado_id]['nombre'] = empleados_dict.get(empleado_id, 'Nombre no encontrado')
        
        # Contar evaluaciones completas (con 9 aspectos) y sumar porcentajes
        for empleado_id, fechas in evaluaciones_agrupadas.items():
            for fecha, evals in fechas.items():
                # Verificar si hay alguna evaluación con ausente=1 para este empleado y fecha
                if any(eval.ausente == 1 for eval in evals):
                    resultados_empleados[empleado_id]['tiene_ausencia'] = True
                
                # Considerar todas las evaluaciones, incluyendo ausentes
                evals_presentes = [eval for eval in evals if eval.ausente == 0]
                
                # Si hay 9 aspectos con ausente=0, consideramos que es una evaluación completa
                if len(evals_presentes) == 9:
                    resultados_empleados[empleado_id]['total_evaluaciones_completas'] += 1
                    # Sumar los porcentajes de todos los aspectos para esta evaluación
                    suma_porcentaje = sum(float(eval.porcentaje_total) for eval in evals_presentes)
                    resultados_empleados[empleado_id]['suma_porcentaje_total'] += suma_porcentaje
        
        # Calcular calificación final por empleado
        detalle_empleados = []
        for empleado_id, datos in resultados_empleados.items():
            if datos['total_evaluaciones_completas'] > 0:
                # Calcular el promedio de porcentaje final (suma de porcentajes / (500 * número de evaluaciones))
                porcentaje_final = (datos['suma_porcentaje_total'] / (500 * datos['total_evaluaciones_completas'])) * 100
                porcentaje_final = min(porcentaje_final, 100.0)  # Limitar a 100%
            else:
                porcentaje_final = 0.0
            
            detalle_empleados.append({
                'empleado_id': empleado_id,
                'nombre': datos['nombre'],
                'calificacion_final': round(porcentaje_final, 2),
                'total_evaluaciones': datos['total_evaluaciones_completas'],
                'tiene_ausencia': datos['tiene_ausencia']
            })
        
        # Ordenar por calificación final de mayor a menor
        detalle_empleados.sort(key=lambda x: x['calificacion_final'], reverse=True)
        
        # Calcular promedio general de todos los empleados
        if detalle_empleados:
            promedio_general = sum(emp['calificacion_final'] for emp in detalle_empleados) / len(detalle_empleados)
        else:
            promedio_general = 0
        
        # Preparar respuesta
        response_data = {
            'total_empleados': len(detalle_empleados),
            'promedio_general': round(promedio_general, 2),
            'detalle_empleados': detalle_empleados
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_blueprint.route('/evaluaciones/aspectos', methods=['OPTIONS', 'GET'])
def obtener_promedio_aspectos():
    try:
        # Consulta con tipo incluido
        query = db.text("""
            SELECT 
                p.texto AS aspecto,
                p.tipo AS tipo,
                COALESCE(ROUND((AVG(e.total_puntos) / 5) * 100, 2), 0.00) AS porcentaje
            FROM 
                aspecto p
            LEFT JOIN 
                evaluacion e ON p.texto = e.aspecto AND e.ausente = FALSE
            GROUP BY 
                p.id, p.texto, p.tipo
            ORDER BY 
                p.id;
        """)

        result = db.session.execute(query)
        data = [
            {
                "aspecto": row.aspecto,
                "tipo": row.tipo,
                "porcentaje": float(row.porcentaje)
            }
            for row in result
        ]

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@routes_blueprint.route('/evaluaciones', methods=['OPTIONS','GET'])
def obtener_evaluaciones():
    #Validar parametros
    encargado_id = request.args.get('encargado_id')
    if not encargado_id:
        return jsonify({'error': 'Se requiere ID de encargado'}), 400

    try:
        # 1. Obtener la fecha de la evaluación más reciente para cada empleado
        subquery = db.session.query(
            Evaluacion.empleado_id,
            db.func.max(Evaluacion.fecha_evaluacion).label('fecha_reciente')
        ).filter(
            Evaluacion.encargado_id == encargado_id
        ).group_by(
            Evaluacion.empleado_id
        ).subquery()

        # 2. Obtener TODAS las evaluaciones más recientes para cada empleado
        evaluaciones = db.session.query(Evaluacion).join(
            subquery,
            db.and_(
                Evaluacion.empleado_id == subquery.c.empleado_id,
                Evaluacion.fecha_evaluacion == subquery.c.fecha_reciente,
                Evaluacion.encargado_id == encargado_id
            )
        ).all()

        if not evaluaciones:
            return jsonify({'error': 'No hay evaluaciones'}), 404

        # Obtener IDs de empleados únicos
        empleado_ids = {eval.empleado_id for eval in evaluaciones}

        # 3. Consultar nombres de empleados
        empleados = db.session.query(Empleado.id, Empleado.nombre).filter(
            Empleado.id.in_(empleado_ids)
        ).all()
        empleados_dict = {emp.id: emp.nombre for emp in empleados}

        # 4. Agrupar evaluaciones por empleado y fecha
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            empleado_id = eval.empleado_id
            evaluaciones_agrupadas[empleado_id][fecha_str].append(eval)
        
        # 5. Procesar datos por empleado
        resultados = defaultdict(lambda: {
            'suma_porcentaje_total': 0.0,
            'total_evaluaciones_completas': 0,
            'nombre': 'Nombre no encontrado',
            'tiene_ausencia': False,
            'fecha_evaluacion': None
        })
        
        # Inicializar datos para todos los empleados
        for empleado_id in empleado_ids:
            resultados[empleado_id]['nombre'] = empleados_dict.get(empleado_id, 'Nombre no encontrado')
        
        # Contar evaluaciones completas (con 9 aspectos) y sumar porcentajes
        for empleado_id, fechas in evaluaciones_agrupadas.items():
            for fecha, evals in fechas.items():
                # Guardar la fecha de evaluación
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                if resultados[empleado_id]['fecha_evaluacion'] is None or fecha_dt > resultados[empleado_id]['fecha_evaluacion']:
                    resultados[empleado_id]['fecha_evaluacion'] = fecha_dt
                
                # Verificar si hay alguna evaluación con ausente=1 para este empleado y fecha
                if any(eval.ausente == 1 for eval in evals):
                    resultados[empleado_id]['tiene_ausencia'] = True
                
                # Solo considerar evaluaciones completas donde ausente=0
                evals_presentes = [eval for eval in evals if eval.ausente == 0]
                
                # Si hay 9 aspectos con ausente=0, consideramos que es una evaluación completa
                if evals_presentes:
                    tipo_eval = evals_presentes[0].tipo_evaluacion
                    total_aspectos_requeridos = 9 if tipo_eval == 1 else 8


                    if len(evals_presentes) == total_aspectos_requeridos:
                        resultados[empleado_id]['total_evaluaciones_completas'] += 1
                        # Sumar los porcentajes de todos los aspectos para esta evaluación
                        suma_porcentaje = sum(float(eval.porcentaje_total) for eval in evals_presentes)
                        resultados[empleado_id]['suma_porcentaje_total'] += suma_porcentaje

        # 6. Calcular porcentaje_final correctamente
        for empleado_id, datos in resultados.items():
            if datos['total_evaluaciones_completas'] > 0:
                # Calcular el promedio de porcentaje final
                # Cada evaluación completa suma 500 puntos (9 aspectos)
                datos['porcentaje_final'] = (datos['suma_porcentaje_total'] / (500 * datos['total_evaluaciones_completas'])) * 100
                datos['porcentaje_final'] = min(datos['porcentaje_final'], 100.0)  # Limitar a 100%
            else:
                datos['porcentaje_final'] = 0.0

        # 7. Calcular promedios solo de empleados con evaluaciones completas y sin ausencias
        promedios = [datos['porcentaje_final'] for empleado_id, datos in resultados.items() 
                    if datos['total_evaluaciones_completas'] > 0]
        promedio_general = sum(promedios) / len(promedios) if promedios else 0

        # 8. Determinar el rango de fechas para el período
        fechas_evaluacion = [datos['fecha_evaluacion'] for datos in resultados.values() if datos['fecha_evaluacion'] is not None]
        if fechas_evaluacion:
            fecha_min = min(fechas_evaluacion)
            fecha_max = max(fechas_evaluacion)
        else:
            # Si no hay fechas, usar la fecha actual
            fecha_min = fecha_max = datetime.now()

        # 9. Formatear respuesta
        return jsonify({
            'promedio_general': round(promedio_general, 2),
            'total_empleados': len(resultados),
            'periodo':{
                'inicio': fecha_min,
                'fin': fecha_max
            },
            'detalle_empleados':[
                {
                    'nombre': datos['nombre'],
                    'empleado_id': emp_id,
                    'calificacion_final': round(datos['porcentaje_final'], 2) if 'porcentaje_final' in datos else 0,
                    'total_evaluaciones': datos['total_evaluaciones_completas'],
                    'tiene_ausencia': datos['tiene_ausencia'],
                    'fecha_evaluacion': datos['fecha_evaluacion'].strftime('%Y-%m-%d') if datos['fecha_evaluacion'] else None
                } for emp_id, datos in resultados.items()
            ]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}),500


# --------------- OBTENER EVALUACIONES COMPLETADAS POR ENCARGADO ----------------------------------------------------------
@routes_blueprint.route('/evaluaciones/completasDestiempoUltimoMes', methods=['OPTIONS', 'GET'])
def obtener_evaluaciones_completas_destiempo_ultimo_mes():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        hoy = datetime.today()
        hace_un_mes = hoy - timedelta(days=30)

        # 1. Obtener el número de empleados por encargado
        subquery_empleados = db.session.query(
            Evaluacion.encargado_id,
            Evaluacion.empleado_id
        ).distinct().subquery()

        empleados_por_encargado = {}
        empleados = db.session.query(
            subquery_empleados.c.encargado_id,
            func.count(subquery_empleados.c.empleado_id)
        ).group_by(subquery_empleados.c.encargado_id).all()

        for encargado_id, total_empleados in empleados:
            empleados_por_encargado[encargado_id] = total_empleados

        # 2. Evaluaciones fuera de tiempo en el último mes
        query = db.session.query(
            Evaluacion.encargado_id,
            Evaluacion.empleado_id,
            func.date(Evaluacion.fecha_evaluacion).label('fecha'),
            Evaluacion.tipo_evaluacion,
            func.count(Evaluacion.id).label('aspectos_count')
        ).filter(
            Evaluacion.a_tiempo == 0,
            Evaluacion.fecha_evaluacion >= hace_un_mes
        ).group_by(
            Evaluacion.encargado_id,
            Evaluacion.empleado_id,
            func.date(Evaluacion.fecha_evaluacion),
            Evaluacion.tipo_evaluacion
        ).all()

        # 3. Agrupar por encargado + fecha
        evaluaciones_temporales = {}

        for encargado_id, empleado_id, fecha, tipo, aspectos in query:
            requisitos = 9 if tipo == 1 else 8
            if aspectos == requisitos:
                key = (encargado_id, fecha)
                if key not in evaluaciones_temporales:
                    evaluaciones_temporales[key] = set()
                evaluaciones_temporales[key].add(empleado_id)

        # 4. Validar que se evaluó a todos los empleados de ese encargado
        evaluaciones_destiempo_completas = {}
        for (encargado_id, fecha), empleados_evaluados in evaluaciones_temporales.items():
            total_esperado = empleados_por_encargado.get(encargado_id, 0)
            if len(empleados_evaluados) == total_esperado:
                if encargado_id not in evaluaciones_destiempo_completas:
                    evaluaciones_destiempo_completas[encargado_id] = 0
                evaluaciones_destiempo_completas[encargado_id] += 1

        if not evaluaciones_destiempo_completas:
            return jsonify({'message': 'No hay evaluaciones completas fuera de tiempo en el último mes'}), 404

        # Obtener nombres de los encargados
        encargado_ids = list(evaluaciones_destiempo_completas.keys())
        encargados = Encargado.query.filter(Encargado.id.in_(encargado_ids)).all()
        encargados_dict = {enc.id: enc.nombre for enc in encargados}

        resultados = [
            {
                'encargado_id': encargado_id,
                'nombre': encargados_dict.get(encargado_id, 'Nombre no encontrado'),
                'evaluaciones_destiempo_completas': total
            }
            for encargado_id, total in evaluaciones_destiempo_completas.items()
        ]

        return jsonify({'resultados': resultados}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --------------- OBTENER EVALUACIONES FILTRADAS ----------------------------------------------------------
@routes_blueprint.route('/evaluaciones/filtradas', methods=['OPTIONS', 'GET'])
def obtener_evaluaciones_filtradas():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Obtener parámetros de filtrado
        encargado_id = request.args.get('encargado_id')
        empleado_id = request.args.get('empleado_id')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        periodo_tipo = request.args.get('periodo_tipo')  # Nuevo parámetro: tipo de periodo (año, mes, semana)
        periodo_valor = request.args.get('periodo_valor')  # Nuevo parámetro: valor del periodo
        debug = request.args.get('debug') == '1'  # Parámetro de depuración
        
        # Información de depuración
        debug_info = {
            'parametros': {
                'encargado_id': encargado_id,
                'empleado_id': empleado_id,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'periodo_tipo': periodo_tipo,
                'periodo_valor': periodo_valor
            },
            'conteos': {}
        }
        
        # Construir la consulta base
        query = Evaluacion.query
        
        # Contar registros iniciales
        total_inicial = query.count()
        debug_info['conteos']['total_inicial'] = total_inicial
        
        # Aplicar filtros si se proporcionan
        if encargado_id:
            query = query.filter(Evaluacion.encargado_id == encargado_id)
            debug_info['conteos']['despues_filtro_encargado'] = query.count()
        
        if empleado_id:
            query = query.filter(Evaluacion.empleado_id == empleado_id)
            debug_info['conteos']['despues_filtro_empleado'] = query.count()
        
        # Filtrar por periodo si se proporciona
        if periodo_tipo and periodo_valor:
            try:
                # Mapear periodo a español
                periodo_mapeado = {
                    'month': 'mes',
                    'year': 'año',
                    'week': 'semana',
                    'mes': 'mes',  # Compatibilidad con español
                    'año': 'año',
                    'semana': 'semana'
                }.get(periodo_tipo, None)
                
                if not periodo_mapeado:
                    raise ValueError('Periodo no válido. Use "month", "year" o "week".')
                
                current_year = datetime.now().year
                
                # Generar fecha_seleccionada según el periodo
                if periodo_mapeado == 'mes':
                    # Si el valor es solo el mes (ej: "05" o "4")
                    if periodo_valor.isdigit() and '-' not in periodo_valor:
                        year = current_year
                        month = int(periodo_valor)
                        fecha_seleccionada = date(year, month, 1)
                    else:
                        # Si en algún caso envía "YYYY-MM"
                        try:
                            year, month = map(int, periodo_valor.split('-'))
                            fecha_seleccionada = date(year, month, 1)
                        except ValueError:
                            raise ValueError(f"Formato de mes inválido: {periodo_valor}. Use MM o YYYY-MM")
                elif periodo_mapeado == 'año':
                    # El valor es el año (ej: "2023")
                    year = int(periodo_valor)
                    fecha_seleccionada = date(year, 1, 1)  # 1 de enero
                elif periodo_mapeado == 'semana':
                    try:
                        if '-' not in periodo_valor:
                            # Caso 1: Solo el número de semana (ej: "15")
                            year = current_year  # Año actual
                            week = int(periodo_valor)
                        else:
                            # Caso 2: Formato YYYY-Www (ej: "2024-W15")
                            # Verificar que el formato sea correcto
                            if not periodo_valor.startswith('W') and 'W' in periodo_valor:
                                parts = periodo_valor.split('-W')
                                if len(parts) != 2:
                                    raise ValueError("Formato inválido para semana. Use YYYY-Www (ej: 2024-W15)")
                                year = int(parts[0])
                                week = int(parts[1])
                            else:
                                raise ValueError("Formato inválido para semana. Use YYYY-Www o solo el número de semana")
                        
                        # Validar rango de la semana
                        if week < 1 or week > 53:
                            raise ValueError("Semana debe estar entre 1 y 53")
                        
                        # Para filtrado por semana, usamos directamente el campo num_semana
                        query = query.filter(Evaluacion.num_semana == week)
                        
                        # Si también se especificó el año, filtramos por año
                        if '-' in periodo_valor:
                            # Extraer el año de la fecha_evaluacion
                            query = query.filter(extract('year', Evaluacion.fecha_evaluacion) == year)
                        
                        debug_info['conteos']['despues_filtro_semana'] = query.count()
                        
                        # No necesitamos calcular fecha_inicio y fecha_fin para semana
                        # ya que filtramos directamente por num_semana
                    except ValueError as e:
                        raise ValueError(f'Error en semana: {str(e)}')
                
                # Calcular rango de fechas para mes y año
                if periodo_mapeado in ['mes', 'año']:
                    fecha_inicio_obj, fecha_fin_obj = calcular_rango_fechas(periodo_mapeado, fecha_seleccionada)
                    
                    if not fecha_inicio_obj or not fecha_fin_obj:
                        raise ValueError('Formato de fecha inválido para el periodo seleccionado')
                    
                    query = query.filter(
                        Evaluacion.fecha_evaluacion >= fecha_inicio_obj,
                        Evaluacion.fecha_evaluacion <= fecha_fin_obj
                    )
                    
                    debug_info['conteos']['despues_filtro_periodo'] = query.count()
            
            except ValueError as e:
                debug_info['errores'] = debug_info.get('errores', []) + [f"Error en periodo: {str(e)}"]
                if debug:
                    return jsonify({'error': str(e), 'debug': debug_info}), 400
                return jsonify({'error': str(e)}), 400
        
        # Filtrar por rango de fechas si se proporcionan (y no se usó periodo)
        elif fecha_inicio or fecha_fin:
            if fecha_inicio:
                try:
                    fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                    query = query.filter(func.date(Evaluacion.fecha_evaluacion) >= fecha_inicio_obj)
                    debug_info['conteos']['despues_filtro_fecha_inicio'] = query.count()
                except ValueError as e:
                    debug_info['errores'] = debug_info.get('errores', []) + [f"Error en fecha_inicio: {str(e)}"]
            
            if fecha_fin:
                try:
                    fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                    query = query.filter(func.date(Evaluacion.fecha_evaluacion) <= fecha_fin_obj)
                    debug_info['conteos']['despues_filtro_fecha_fin'] = query.count()
                except ValueError as e:
                    debug_info['errores'] = debug_info.get('errores', []) + [f"Error en fecha_fin: {str(e)}"]
        
        # Ejecutar la consulta
        evaluaciones = query.all()
        debug_info['conteos']['total_evaluaciones'] = len(evaluaciones)
        
        if not evaluaciones:
            if debug:
                return jsonify({'resultados': [], 'debug': debug_info}), 200
            return jsonify([]), 200  # Devolver array vacío si no hay resultados
        
        # El resto de la función permanece igual
        # Agrupar evaluaciones por empleado, encargado y fecha
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            empleado_id = eval.empleado_id
            encargado_id = eval.encargado_id
            evaluaciones_agrupadas[empleado_id][encargado_id][fecha_str].append(eval)
        
        # Obtener información de empleados y encargados
        empleado_ids = set(eval.empleado_id for eval in evaluaciones)
        encargado_ids = set(eval.encargado_id for eval in evaluaciones)
        
        debug_info['ids'] = {
            'empleado_ids': list(empleado_ids),
            'encargado_ids': list(encargado_ids)
        }
        
        empleados = Empleado.query.filter(Empleado.id.in_(empleado_ids)).all()
        encargados = Encargado.query.filter(Encargado.id.in_(encargado_ids)).all()
        
        debug_info['conteos']['empleados_encontrados'] = len(empleados)
        debug_info['conteos']['encargados_encontrados'] = len(encargados)
        
        empleados_dict = {emp.id: emp for emp in empleados}
        encargados_dict = {enc.id: enc for enc in encargados}
        
        # Procesar resultados
        resultados = []
        empleados_no_encontrados = []
        encargados_no_encontrados = []
        
        for emp_id, encargados_data in evaluaciones_agrupadas.items():
            empleado = empleados_dict.get(emp_id)
            
            if not empleado:
                empleados_no_encontrados.append(emp_id)
                continue  # Saltar si no se encuentra el empleado
            
            for enc_id, fechas_data in encargados_data.items():
                encargado = encargados_dict.get(enc_id)
                
                if not encargado:
                    encargados_no_encontrados.append(enc_id)
                    continue  # Saltar si no se encuentra el encargado
                
                for fecha, evals in fechas_data.items():
                    # Verificar si hay alguna evaluación con ausente=1
                    ausente = any(eval.ausente == 1 for eval in evals)
                    
                    # Si está ausente, no procesamos los aspectos
                    if ausente:
                        resultados.append({
                            'fecha': fecha,
                            'empleado_id': emp_id,
                            'empleado_nombre': empleado.nombre,
                            'encargado_id': enc_id,
                            'encargado_nombre': encargado.nombre,
                            'ausente': True,
                            'comentarios': evals[0].comentarios if evals else '',
                            'calificacion_total': 0,
                            'aspectos': []
                        })
                    else:
                        # Procesar aspectos para evaluaciones donde el empleado estuvo presente
                        aspectos = []
                        suma_porcentaje = 0
                        
                        for eval in evals:
                            aspectos.append({
                                'aspecto': eval.aspecto,
                                'calificacion': eval.total_puntos,
                                'porcentaje': eval.porcentaje_total
                            })
                            suma_porcentaje += float(eval.porcentaje_total)
                        
                        # Calcular calificación total (sobre 100%)
                        calificacion_total = (suma_porcentaje / 500) * 100 if len(evals) > 0 else 0
                        
                        resultados.append({
                            'fecha': fecha,
                            'empleado_id': emp_id,
                            'empleado_nombre': empleado.nombre,
                            'encargado_id': enc_id,
                            'encargado_nombre': encargado.nombre,
                            'ausente': False,
                            'comentarios': evals[0].comentarios if evals else '',
                            'calificacion_total': round(calificacion_total, 2),
                            'aspectos': aspectos
                        })
        
        debug_info['errores_procesamiento'] = {
            'empleados_no_encontrados': empleados_no_encontrados,
            'encargados_no_encontrados': encargados_no_encontrados
        }
        
        debug_info['conteos']['resultados_finales'] = len(resultados)
        
        # Ordenar por fecha (más reciente primero)
        resultados.sort(key=lambda x: x['fecha'], reverse=True)
        
        if debug:
            return jsonify({'resultados': resultados, 'debug': debug_info}), 200
        return jsonify(resultados), 200
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        return jsonify({
            'error': str(e),
            'traceback': error_traceback
        }), 500

@routes_blueprint.route('/evaluaciones/exportar-csv', methods=['OPTIONS', 'GET'])
def exportar_evaluaciones_csv():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print("\n=== PARÁMETROS RECIBIDOS PARA EXPORTACIÓN ===")
        print(f"periodo_tipo: {request.args.get('periodo_tipo')}")
        print(f"periodo_valor: {request.args.get('periodo_valor')}")
        print(f"agrupar: {request.args.get('agrupar', 'false')}")

        # Obtener parámetros
        periodo = request.args.get('periodo_tipo', 'mes')
        periodo_valor = request.args.get('periodo_valor')
        agrupar = request.args.get('agrupar', 'false').lower() == 'true'  # Nuevo parámetro para agrupar
        current_year = datetime.now().year
        
        # Validar parámetros
        if not periodo_valor:
            return jsonify({'error': 'Se requiere periodo_valor'}), 400

        # Mapear periodo a español
        periodo_mapeado = {
            'month': 'mes',
            'year': 'año',
            'week': 'semana',
            'mes': 'mes',  # Compatibilidad con español
            'año': 'año',
            'semana': 'semana'
        }.get(periodo, None)

        if not periodo_mapeado:
            return jsonify({'error': 'Periodo no válido. Use "month", "year" o "week".'}), 400

        # Generar fecha_seleccionada según el periodo
        try:
            if periodo_mapeado == 'mes':
                # Si el valor es solo el mes (ej: "05" o "4")
                if periodo_valor.isdigit() and '-' not in periodo_valor:
                    year = current_year
                    month = int(periodo_valor)
                    fecha_seleccionada = date(year, month, 1)
                else:
                    # Si en algún caso envía "YYYY-MM"
                    try:
                        year, month = map(int, periodo_valor.split('-'))
                        fecha_seleccionada = date(year, month, 1)
                    except ValueError:
                        raise ValueError(f"Formato de mes inválido: {periodo_valor}. Use MM o YYYY-MM")
            elif periodo_mapeado == 'año':
                # El valor es el año (ej: "2023")
                year = int(periodo_valor)
                fecha_seleccionada = date(year, 1, 1)  # 1 de enero
            elif periodo_mapeado == 'semana':
                try:
                    if '-' not in periodo_valor:
                        # Caso 1: Solo el número de semana (ej: "15")
                        year = current_year  # Año actual
                        week = int(periodo_valor)
                    else:
                        # Caso 2: Formato YYYY-Www (ej: "2024-W15")
                        # Verificar que el formato sea correcto
                        if not periodo_valor.startswith('W') and 'W' in periodo_valor:
                            parts = periodo_valor.split('-W')
                            if len(parts) != 2:
                                raise ValueError("Formato inválido para semana. Use YYYY-Www (ej: 2024-W15)")
                            year = int(parts[0])
                            week = int(parts[1])
                        else:
                            raise ValueError("Formato inválido para semana. Use YYYY-Www o solo el número de semana")
                    
                    # Validar rango de la semana
                    if week < 1 or week > 53:
                        raise ValueError("Semana debe estar entre 1 y 53")
                    
                    fecha_seleccionada = datetime.fromisocalendar(year, week, 1).date()
                
                except ValueError as e:
                    return jsonify({'error': f'Error en semana: {str(e)}'}), 400
        except ValueError as e:
            return jsonify({'error': f'Error: {str(e)}'}), 400

        # Validaciones adicionales
        if periodo_mapeado == 'mes' and not (1 <= fecha_seleccionada.month <= 12):
            return jsonify({'error': 'Mes inválido (debe ser 1-12)'}), 400

        if periodo_mapeado == 'semana' and not (1 <= fecha_seleccionada.isocalendar()[1] <= 53):
            return jsonify({'error': 'Semana inválida (1-53)'}), 400

        if periodo_mapeado == 'año' and not (2000 <= fecha_seleccionada.year <= 2100):
            return jsonify({'error': 'Año inválido (2000-2100)'}), 400

        # Calcular rango de fechas
        fecha_inicio, fecha_fin = calcular_rango_fechas(periodo_mapeado, fecha_seleccionada)
        
        if not fecha_inicio or not fecha_fin:
            return jsonify({'error': 'Formato de fecha inválido para el periodo seleccionado'}), 400
        
        # Construir la consulta base para obtener todas las evaluaciones en el rango
        query = Evaluacion.query.filter(
            Evaluacion.fecha_evaluacion >= fecha_inicio,
            Evaluacion.fecha_evaluacion <= fecha_fin
        ).order_by(Evaluacion.empleado_id, Evaluacion.fecha_evaluacion)
        
        # Ejecutar la consulta
        evaluaciones = query.all()
        
        if not evaluaciones:
            return jsonify({'message': 'No hay evaluaciones para los filtros seleccionados'}), 404
        
        # Obtener IDs de empleados y encargados únicos
        empleado_ids = {eval.empleado_id for eval in evaluaciones}
        encargado_ids = {eval.encargado_id for eval in evaluaciones}
        
        # Consultar nombres de empleados
        empleados = db.session.query(Empleado.id, Empleado.nombre).filter(
            Empleado.id.in_(empleado_ids)
        ).all()
        empleados_dict = {emp.id: emp.nombre for emp in empleados}
        
        # Consultar nombres de encargados
        encargados = db.session.query(Encargado.id, Encargado.nombre).filter(
            Encargado.id.in_(encargado_ids)
        ).all()
        encargados_dict = {enc.id: enc.nombre for enc in encargados}
        
        # Agrupar evaluaciones por empleado, fecha y encargado
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            empleado_id = eval.empleado_id
            encargado_id = eval.encargado_id
            evaluaciones_agrupadas[empleado_id][fecha_str][encargado_id].append(eval)

        # Calcular promedios para evaluaciones completas (9 aspectos)
        promedios_evaluaciones = {}  # (empleado_id, fecha, encargado_id) -> promedio
        for empleado_id, fechas in evaluaciones_agrupadas.items():
            for fecha, encargados in fechas.items():
                for encargado_id, evals in encargados.items():
                    # Si hay 9 aspectos, consideramos que es una evaluación completa
                    if len(evals) == 9:
                        # Sumar los porcentajes de todos los aspectos para esta evaluación
                        suma_porcentaje = sum(float(eval.porcentaje_total) for eval in evals)
                        # Calcular promedio (sobre 100%)
                        promedio = (suma_porcentaje / 500) * 100
                        # Guardar el promedio
                        promedios_evaluaciones[(empleado_id, fecha, encargado_id)] = round(promedio, 2)

        # Preparar datos para exportación CSV
        datos_exportacion = []
        
        if agrupar:
            # Exportar evaluaciones agrupadas (1 fila por evaluación completa)
            for empleado_id, fechas in evaluaciones_agrupadas.items():
                for fecha, encargados in fechas.items():
                    for encargado_id, evals in encargados.items():
                        # Solo incluir evaluaciones completas (9 aspectos)
                        if len(evals) == 9:
                            # Calcular promedio
                            promedio = promedios_evaluaciones.get((empleado_id, fecha, encargado_id), 0)
                            
                            # Verificar si hay ausencia
                            ausente = any(eval.ausente for eval in evals)
                            
                            # Verificar si está a tiempo
                            a_tiempo = all(eval.a_tiempo for eval in evals)
                            
                            # Obtener comentarios (normalmente son iguales para todos los aspectos)
                            comentarios = evals[0].comentarios if evals else ""
                            
                            # Crear una fila para la evaluación completa
                            datos_exportacion.append({
                                'Fecha': fecha,
                                'Nombre Empleado': empleados_dict.get(empleado_id, 'Desconocido'),
                                'Nombre Encargado': encargados_dict.get(encargado_id, 'Desconocido'),
                                'Calificación Promedio': promedio,
                                'Comentarios': comentarios
                            })
        else:
            # Exportar todos los aspectos individuales (formato original)
            for eval in evaluaciones:
                fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
                empleado_id = eval.empleado_id
                encargado_id = eval.encargado_id
                
                # Obtener el promedio si existe (evaluación completa)
                promedio = promedios_evaluaciones.get((empleado_id, fecha_str, encargado_id), None)
                
                datos_exportacion.append({
                    'Fecha': fecha_str,
                    'Nombre Empleado': empleados_dict.get(empleado_id, 'Desconocido'),
                    'Nombre Encargado': encargados_dict.get(encargado_id, 'Desconocido'),
                    'Puntuación': eval.total_puntos,
                    'Porcentaje': eval.porcentaje_total,
                    'Promedio Evaluación': promedio if promedio is not None else 'N/A'
                })
        
        # Formatear el periodo para la respuesta
        periodo_formateado = formatear_periodo(periodo, fecha_inicio)
        
        # Preparar respuesta con metadatos
        response_data = {
            'periodo': periodo_formateado,
            'rango_fechas': {
                'inicio': fecha_inicio.strftime('%Y-%m-%d'),
                'fin': fecha_fin.strftime('%Y-%m-%d')
            },
            'total_registros': len(datos_exportacion),
            'agrupado': agrupar,
            'datos': datos_exportacion
        }
        
        formato = request.args.get('formato', 'json')
        
        if formato.lower() == 'csv':
            # Generate CSV directly
            import csv
            import io
            
            # Create a string buffer for the CSV data
            output = io.StringIO()
            
            # Get field names from the first item
            if datos_exportacion:
                fieldnames = list(datos_exportacion[0].keys())
                
                # Create CSV writer
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                
                # Write header and rows
                writer.writeheader()
                writer.writerows(datos_exportacion)
                
                # Get the CSV data as a string
                csv_data = output.getvalue()
                
                # Create response with CSV data
                response = make_response(csv_data)
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = f'attachment; filename=evaluaciones_{periodo_formateado}.csv'
                
                return response
            else:
                return jsonify({'error': 'No hay datos para exportar'}), 404
        
        # If not CSV, return JSON as before
        response_data = {
            'periodo': periodo_formateado,
            'rango_fechas': {
                'inicio': fecha_inicio.strftime('%Y-%m-%d'),
                'fin': fecha_fin.strftime('%Y-%m-%d')
            },
            'total_registros': len(datos_exportacion),
            'agrupado': agrupar,
            'datos': datos_exportacion
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Error en exportación CSV: {str(e)}")
        return jsonify({'error': str(e)}), 500
        

def calcular_rango_fechas(periodo, fecha_seleccionada):
    """Calcula el rango de fechas basado en el periodo y la fecha seleccionada."""
    try:
        from dateutil.relativedelta import relativedelta
        
        if periodo == 'año':
            # Para año, usamos el año de la fecha_seleccionada
            año = fecha_seleccionada.year
            fecha_inicio = datetime(año, 1, 1)
            fecha_fin = datetime(año, 12, 31, 23, 59, 59)
            
        elif periodo == 'mes':
            # Para mes, usamos el año y mes de la fecha_seleccionada
            año = fecha_seleccionada.year
            mes = fecha_seleccionada.month
            fecha_inicio = datetime(año, mes, 1)
            
            # Último día del mes
            if mes == 12:
                fecha_fin = datetime(año + 1, 1, 1) - timedelta(seconds=1)
            else:
                fecha_fin = datetime(año, mes + 1, 1) - timedelta(seconds=1)
                
        elif periodo == 'semana':
            # Para semana, usamos la fecha_seleccionada directamente
            # que ya debe ser el primer día de la semana
            fecha_inicio = datetime.combine(fecha_seleccionada, datetime.min.time())
            # Último día de la semana (domingo)
            fecha_fin = fecha_inicio + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
        return fecha_inicio, fecha_fin
        
    except Exception as e:
        print(f"Error calculando rango de fechas: {e}")
        return None, None

def formatear_periodo(periodo, fecha_inicio):
    """Formatea el periodo para la respuesta según el tipo de periodo."""
    if periodo == 'año':
        return fecha_inicio.strftime('%Y')
    elif periodo == 'mes':
        return fecha_inicio.strftime('%Y-%m')
    elif periodo == 'semana':
        # ISO 8601 formato de semana: YYYY-Www
        año = fecha_inicio.isocalendar()[0]
        semana = fecha_inicio.isocalendar()[1]
        return f"{año}-W{semana:02d}"
    return ""

# --------------- OBTENER PROMEDIO POR ENCARGADO ----------------------------------------------------------
@routes_blueprint.route('/evaluaciones/promedio-encargados', methods=['OPTIONS', 'GET'])
def obtener_promedio_encargados():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Obtener todas las evaluaciones (incluyendo ausentes)
        evaluaciones = Evaluacion.query.all()
        
        if not evaluaciones:
            return jsonify({'error': 'No hay evaluaciones disponibles'}), 404
        
        # Obtener IDs de encargados únicos
        encargado_ids = {eval.encargado_id for eval in evaluaciones}
        
        # Consultar nombres e información de encargados
        encargados = Encargado.query.filter(Encargado.id.in_(encargado_ids)).all()
        encargados_dict = {enc.id: {
            'nombre': enc.nombre,
            'tipo_evaluacion': enc.tipo_evaluacion
        } for enc in encargados}
        
        # Agrupar evaluaciones por encargado y fecha
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            encargado_id = eval.encargado_id
            evaluaciones_agrupadas[encargado_id][fecha_str].append(eval)
        
        # Procesar datos por encargado
        resultados_encargados = defaultdict(lambda: {
            'suma_porcentaje_total': 0.0,
            'total_evaluaciones_completas': 0,
            'nombre': 'Nombre no encontrado',
            'total_empleados_evaluados': set(),
            'tipo_evaluacion': 0
        })
        
        # Contar evaluaciones completas y sumar porcentajes según el tipo de encargado
        for encargado_id, fechas in evaluaciones_agrupadas.items():
            # Obtener el tipo de evaluación del encargado
            tipo_encargado = encargados_dict.get(encargado_id, {}).get('tipo_evaluacion', 0)
            resultados_encargados[encargado_id]['tipo_evaluacion'] = tipo_encargado
            resultados_encargados[encargado_id]['nombre'] = encargados_dict.get(encargado_id, {}).get('nombre', 'Nombre no encontrado')
            
            for fecha, evals in fechas.items():
                # Filtrar evaluaciones donde ausente=0 (no ausentes)
                evals_presentes = [e for e in evals if e.ausente == 0]
                
                if not evals_presentes:
                    continue  # Si todas las evaluaciones son de ausentes, saltamos
                
                # Agrupar por empleado para verificar evaluaciones completas
                empleados_evaluados = {}
                for eval in evals_presentes:
                    if eval.empleado_id not in empleados_evaluados:
                        empleados_evaluados[eval.empleado_id] = []
                    empleados_evaluados[eval.empleado_id].append(eval)
                
                # Verificar evaluaciones completas por empleado
                for empleado_id, evals_empleado in empleados_evaluados.items():
                    # Determinar si la evaluación está completa según el tipo de encargado
                    es_completa = False
                    aspectos_requeridos = 9 if tipo_encargado == 1 else 8
                    
                    if len(evals_empleado) == aspectos_requeridos:
                        es_completa = True
                    
                    if es_completa:
                        resultados_encargados[encargado_id]['total_evaluaciones_completas'] += 1
                        resultados_encargados[encargado_id]['total_empleados_evaluados'].add(empleado_id)
                        
                        # Sumar los porcentajes de todos los aspectos para esta evaluación
                        suma_porcentaje = sum(float(eval.porcentaje_total) for eval in evals_empleado)
                        resultados_encargados[encargado_id]['suma_porcentaje_total'] += suma_porcentaje
        
        # Calcular calificación promedio por encargado
        detalle_encargados = []
        for encargado_id, datos in resultados_encargados.items():
            if datos['total_evaluaciones_completas'] > 0:
                # Calcular el promedio según el tipo de encargado
                tipo_encargado = datos['tipo_evaluacion']
                divisor = 500  # Valor por defecto para tipo 1 (9 aspectos)
                
                if tipo_encargado == 2:
                    divisor = 400  # Para tipo 2 (8 aspectos)
                
                # Calcular el promedio de porcentaje final
                porcentaje_final = (datos['suma_porcentaje_total'] / (divisor * datos['total_evaluaciones_completas'])) * 100
                porcentaje_final = min(porcentaje_final, 100.0)  # Limitar a 100%
                
                detalle_encargados.append({
                    'encargado_id': encargado_id,
                    'nombre': datos['nombre'],
                    'tipo_evaluacion': tipo_encargado,
                    'calificacion_promedio': round(porcentaje_final, 2),
                    'total_evaluaciones': datos['total_evaluaciones_completas'],
                    'total_empleados_evaluados': len(datos['total_empleados_evaluados'])
                })
        
        # Ordenar por calificación promedio de mayor a menor
        detalle_encargados.sort(key=lambda x: x['calificacion_promedio'], reverse=True)
        
        # Calcular promedio general de todos los encargados
        if detalle_encargados:
            promedio_general = sum(enc['calificacion_promedio'] for enc in detalle_encargados) / len(detalle_encargados)
        else:
            promedio_general = 0
        
        # Preparar respuesta
        response_data = {
            'total_encargados': len(detalle_encargados),
            'promedio_general': round(promedio_general, 2),
            'detalle_encargados': detalle_encargados
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------- EVALUACIONES POR EMPLEADO ------------------------------------------------------------------------------
@routes_blueprint.route('/evaluaciones/empleado/<int:empleado_id>', methods=['OPTIONS', 'GET'])
def obtener_evaluaciones_empleado(empleado_id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Obtener parámetros de filtro con nuevos nombres
        periodo = request.args.get('periodo_tipo', 'mes')  # Valores posibles: 'month', 'week', 'year'
        periodo_valor = request.args.get('periodo_valor')  # Puede ser "3" para marzo, "2024-03", "15" para semana, etc.
        current_year = datetime.now().year
        
        # Validar que el empleado existe
        empleado = Empleado.query.get(empleado_id)
        if not empleado:
            return jsonify({'error': 'Empleado no encontrado'}), 404
        
        # Mapear periodo a español
        periodo_mapeado = {
            'month': 'mes',
            'year': 'año',
            'week': 'semana',
            'mes': 'mes',
            'año': 'año',
            'semana': 'semana'
        }.get(periodo, None)

        if not periodo_mapeado:
            return jsonify({'error': 'Periodo no válido. Use "month", "year" o "week".'}), 400
            
        # Generar fecha_seleccionada según el periodo
        try:
            if periodo_mapeado == 'mes':
                # Si el valor es solo el mes (ej: "05" o "4")
                if periodo_valor and periodo_valor.isdigit() and '-' not in periodo_valor:
                    year = current_year
                    month = int(periodo_valor)
                    fecha_seleccionada = date(year, month, 1)
                else:
                    # Si en algún caso envía "YYYY-MM"
                    try:
                        year, month = map(int, periodo_valor.split('-'))
                        fecha_seleccionada = date(year, month, 1)
                    except (ValueError, AttributeError):
                        raise ValueError(f"Formato de mes inválido: {periodo_valor}. Use MM o YYYY-MM")
            elif periodo_mapeado == 'año':
                # El valor es el año (ej: "2023")
                year = int(periodo_valor)
                fecha_seleccionada = date(year, 1, 1)  # 1 de enero
            elif periodo_mapeado == 'semana':
                try:
                    if '-' not in periodo_valor:
                        # Caso 1: Solo el número de semana (ej: "15")
                        year = current_year  # Año actual
                        week = int(periodo_valor)
                    else:
                        # Caso 2: Formato YYYY-Www (ej: "2024-W15")
                        # Verificar que el formato sea correcto
                        if not periodo_valor.startswith('W') and 'W' in periodo_valor:
                            parts = periodo_valor.split('-W')
                            if len(parts) != 2:
                                raise ValueError("Formato inválido para semana. Use YYYY-Www (ej: 2024-W15)")
                            year = int(parts[0])
                            week = int(parts[1])
                        else:
                            raise ValueError("Formato inválido para semana. Use YYYY-Www o solo el número de semana")
                    
                    # Validar rango de la semana
                    if week < 1 or week > 53:
                        raise ValueError("Semana debe estar entre 1 y 53")
                    
                    fecha_seleccionada = datetime.fromisocalendar(year, week, 1).date()
                
                except ValueError as e:
                    return jsonify({'error': f'Error en semana: {str(e)}'}), 400
        except ValueError as e:
            # Si hay error o no se proporciona periodo_valor, usar el mes actual
            hoy = datetime.now()
            fecha_seleccionada = date(hoy.year, hoy.month, 1)
            periodo_mapeado = 'mes'  # Forzar a mes como valor predeterminado

        # Calcular rango de fechas usando la función existente
        fecha_inicio, fecha_fin = calcular_rango_fechas(periodo_mapeado, fecha_seleccionada)
        
        if not fecha_inicio or not fecha_fin:
            return jsonify({'error': 'Formato de fecha inválido para el periodo seleccionado'}), 400
        
        # Construir la consulta base
        query = Evaluacion.query.filter(
            Evaluacion.empleado_id == empleado_id,
            Evaluacion.fecha_evaluacion >= fecha_inicio,
            Evaluacion.fecha_evaluacion <= fecha_fin
        )
        
        # Ejecutar la consulta
        evaluaciones = query.order_by(Evaluacion.fecha_evaluacion.desc()).all()
        
        if not evaluaciones:
            return jsonify({
                'empleado_id': empleado_id,
                'empleado_nombre': empleado.nombre,
                'periodo': formatear_periodo(periodo_mapeado, fecha_seleccionada),
                'rango_fechas': {
                    'inicio': fecha_inicio.strftime('%Y-%m-%d'),
                    'fin': fecha_fin.strftime('%Y-%m-%d')
                },
                'message': 'No hay evaluaciones para este empleado en el período seleccionado',
                'evaluaciones': []
            }), 200
        
        # El resto de la función permanece igual
        # Agrupar evaluaciones por fecha y encargado
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        for eval in evaluaciones:
            # Check if fecha_evaluacion is a datetime or date object
            fecha_local = eval.fecha_evaluacion
            if isinstance(fecha_local, datetime):
                # Only try to handle timezone if it's a datetime object
                if fecha_local.tzinfo is not None:
                    # If the date has timezone info, convert to local timezone
                    fecha_local = fecha_local.astimezone(pytz.timezone('America/Mexico_City'))
            
            # Format the date as string
            fecha_str = fecha_local.strftime('%Y-%m-%d')
            encargado_id = eval.encargado_id
            evaluaciones_agrupadas[fecha_str][encargado_id].append(eval)
        
        # Obtener información de encargados
        encargado_ids = {eval.encargado_id for eval in evaluaciones}
        encargados = Encargado.query.filter(Encargado.id.in_(encargado_ids)).all()
        encargados_dict = {enc.id: enc.nombre for enc in encargados}
        
        # Procesar resultados
        resultados = []
        for fecha, encargados_eval in evaluaciones_agrupadas.items():
            for encargado_id, evals in encargados_eval.items():
                # Verificar si hay alguna evaluación con ausente=1
                ausente = any(eval.ausente == 1 for eval in evals)
                
                # Si está ausente, no procesamos los aspectos
                if ausente:
                    resultados.append({
                        'fecha': fecha,
                        'encargado_id': encargado_id,
                        'encargado_nombre': encargados_dict.get(encargado_id, 'Desconocido'),
                        'ausente': True,
                        'comentarios': evals[0].comentarios if evals else '',
                        'calificacion_total': 0,
                        'aspectos': []
                    })
                else:
                    # Procesar aspectos para evaluaciones donde el empleado estuvo presente
                    aspectos = []
                    suma_porcentaje = 0
                    
                    for eval in evals:
                        aspectos.append({
                            'aspecto': eval.aspecto,
                            'calificacion': eval.total_puntos,
                            'porcentaje': eval.porcentaje_total
                        })
                        suma_porcentaje += float(eval.porcentaje_total)
                    
                    # Calcular calificación total (sobre 100%)
                    calificacion_total = (suma_porcentaje / 500) * 100 if len(evals) == 9 else 0
                    
                    resultados.append({
                        'fecha': fecha,
                        'encargado_id': encargado_id,
                        'encargado_nombre': encargados_dict.get(encargado_id, 'Desconocido'),
                        'ausente': False,
                        'comentarios': evals[0].comentarios if evals else '',
                        'calificacion_total': round(calificacion_total, 2),
                        'aspectos': aspectos
                    })
        
        # Formatear el periodo para la respuesta
        periodo_formateado = formatear_periodo(periodo_mapeado, fecha_seleccionada)
        
        return jsonify({
            'empleado_id': empleado_id,
            'empleado_nombre': empleado.nombre,
            'periodo': periodo_formateado,
            'rango_fechas': {
                'inicio': fecha_inicio.strftime('%Y-%m-%d'),
                'fin': fecha_fin.strftime('%Y-%m-%d')
            },
            'evaluaciones': resultados
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500