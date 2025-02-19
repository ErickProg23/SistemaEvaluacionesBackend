from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from .models import Usuario, Rol, Empleado, Encargado, Pregunta
from flask_cors import CORS
from app import db
from datetime import datetime
from sqlalchemy import func
from . import jwt, bcrypt  # Asegúrate de que `bcrypt` esté configurado en tu archivo principal


# Crear un Blueprint para las rutas
routes_blueprint = Blueprint('routes', __name__)

@jwt.user_identity_loader
def user_identity_lookup(user):
    return user  # Ajusta esto según el campo de identidad único de tu modelo de usuario

#LOGIN --------------------------------------------------------------------------------------------
@routes_blueprint.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    correo = data.get('correo')
    contrasena = data.get('contrasena')
    nombre = data.get('nombre')

    # Busca al usuario en la base de datos
    usuario = Usuario.query.filter_by(correo=correo).first()

    if contrasena and usuario.contrasena == contrasena:
        # Generar un token de acceso
        access_token = create_access_token(identity={'correo': usuario.correo})

        # Recupera el rol_id del usuario
        rol_id = usuario.rol_id  # Asegúrate de que `Usuario` tiene una columna llamada `rol_id`

        # Busca si el usuario tiene un registro en la tabla encargado
        encargado = Encargado.query.filter_by(usuario_id=usuario.id).first()

        # Si el encargado existe, obtenemos su ID
        id_encargado = encargado.id if encargado else None

        nombre = usuario.nombre
        
        return jsonify({'access_token': access_token}
        , {'rol_id': rol_id}
        , {'nombre': nombre},
        {'id_encargado': id_encargado}), 200

    return jsonify({'message': 'Correo o contraseña incorrectos'}), 401


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
                'activo': empleado.activo
            }
            for empleado in empleados
        ]

        return jsonify(empleados_data), 200

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

@routes_blueprint.route('/preguntas', methods=['GET'])
def obtener_preguntas():
    # Obtiene todas las preguntas
    preguntas = Pregunta.query.all()

    if not preguntas:
        return jsonify({"mensaje": "No hay preguntas disponibles"}), 404

    # Convertir los objetos en formato JSON
    preguntas_json = [pregunta.to_dict() for pregunta in preguntas]

    return jsonify(preguntas_json), 200


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

    nombre = data.get('nombre')
    puesto = data.get('puesto')
    num_empleado = data.get('num_empleado')
    encargados_ids = data.get('encargados_ids', [])
    rol_id = data.get('rol_id', 3)

    if not nombre or not puesto or not num_empleado:
        return jsonify({'error': 'Faltan datos'}), 400

    try:
        nuevo_empleado = Empleado(
            nombre=nombre,
            puesto=puesto,
            num_empleado=num_empleado,
            rol_id=rol_id
        )
        db.session.add(nuevo_empleado)
        db.session.flush()

        # Relacionar los encargados seleccionados con el empleado
        if encargados_ids:
            encargados = Encargado.query.filter(Encargado.id.in_(encargados_ids)).all()
            if not encargados:
                return jsonify({'error': 'Uno o más encargados no encontrados'}), 404
            nuevo_empleado.encargados.extend(encargados)  # Asignar la relación muchos a muchos

        db.session.commit()

        return jsonify({
            'message': 'Empleado creado correctamente',
            'empleado': {
                'id': nuevo_empleado.id,
                'nombre': nuevo_empleado.nombre,
                'puesto': nuevo_empleado.puesto,
                'num_empleado': nuevo_empleado.num_empleado,
                'encargados': [encargado.nombre for encargado in nuevo_empleado.encargados],
                'rol': nuevo_empleado.rol_id
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error':'Error al crear el empleado', 'mensaje': str(e)}), 500


@routes_blueprint.route('/encargados/nuevo', methods=['OPTIONS', 'POST'])
def nuevo_encargado():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No se recibio datos'}), 400

    nombre = data.get('nombre')
    puesto = data.get('puesto')
    num_empleado = data.get('num_empleado')
    encargados_ids = data.get('encargados_ids', [])
    rol_id = data.get('rol_id',2)

    if not nombre or not puesto or not num_empleado:
        return jsonify({'error': 'Faltan datos'}), 400

    try:

        nuevo_encargado = Encargado(
            nombre=nombre,
            puesto=puesto,
            num_empleado=num_empleado,
            rol_id=rol_id
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



# Guardar proceso -------------------------------------------------------------------------------------------------------
