from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from .models import Usuario, Rol, Empleado, Encargado
from flask_cors import CORS
from app import db
from datetime import datetime
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

        nombre = usuario.nombre
        
        return jsonify({'access_token': access_token}
        , {'rol_id': rol_id}
        , {'nombre': nombre}), 200

    return jsonify({'message': 'Correo o contraseña incorrectos'}), 401


#OBTENER DATOS --------------------------------------------------------------------------------------------

@routes_blueprint.route('/usuarios/empleados', methods=['GET'])
def get_empleados():
    empleados = Empleado.query.filter_by(rol_id=3)

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
        encargados_data = [{'id': encargado.id, 'nombre': encargado.nombre, 'activo': encargado.activo, 'puesto': encargado.puesto, 'num_empleado': encargado.num_empleado} 
                            for encargado in encargados]
        return jsonify(encargados_data), 200
    else:
        return jsonify({'message': 'No se pudo extraer la informacion'}), 401


@routes_blueprint.route('/usuarios/empleados/<int:id>', methods=['GET'])
def obtener_empleados(id):
    empleados = Empleado.query.filter_by(evaluador_id=id).all()

    # Verifica si se encontraron empleados
    if empleados:
        # Itera sobre la lista de empleados y crea un diccionario con los datos necesarios
        empleados_data = [{'id': empleado.id, 'nombre': empleado.nombre, 
                           'puesto': empleado.puesto, 'num_empleado': empleado.num_empleado, 'activo': empleado.activo}
                          for empleado in empleados]
        return jsonify(empleados_data), 200
    else:
        return jsonify({'message': 'No se pudo extraer la informacion'}), 401

@routes_blueprint.route('/usuarios/mayores', methods=['GET'])
def get_mayores():
    usuarios = Usuario.query.filter_by(rol_id=4).all()

    if usuarios:
        usuarios_data = [{'id': usuario.id, 'nombre': usuario.nombre, 'rol_id': usuario.rol_id} 
        for usuario in  usuarios]
        return jsonify(usuarios_data), 200
    else:
        return jsonify({'message': 'No se pudo extraer la informacion'}), 401


        
@routes_blueprint.route('/usuarios/empleado/<int:id>', methods=['GET'])
def obtener_empleado(id):
    # Obtiene al empleado con su evaluador
    empleado = Empleado.query.filter_by(id=id).first()

    if empleado:
        # Construcción del resultado con la información del evaluador
        empleado_data = {
            'id': empleado.id,
            'nombre': empleado.nombre,
            'puesto': empleado.puesto,
            'num_empleado': empleado.num_empleado,
            'activo': empleado.activo,
            'evaluador': {
                'id': empleado.evaluador.id if empleado.evaluador else None,
                'nombre': empleado.evaluador.nombre if empleado.evaluador else 'Sin encargado'
            }
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
        encargado_data = {
            'id': encargado.id,
            'nombre': encargado.nombre,
            'puesto': encargado.puesto,
            'num_empleado': encargado.num_empleado,
            'activo': encargado.activo,
            'evaluador': {
                'id': encargado.evaluador.id if encargado.evaluador else None,
                'nombre': encargado.evaluador.nombre if encargado.evaluador else 'Sin encargado'
            }
        }
        return jsonify(encargado_data), 200
    else:
        return jsonify({'message': 'No se pudo extraer la información'}), 404


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
    empleado.evaluador_id = data['evaluador_id']
    db.session.commit()
        
    return jsonify({'message': 'Empleado editado correctamente'}), 200


@routes_blueprint.route('/encargado/editar/<int:id>', methods =['PUT'])
def editar_encargado(id):
    # Manejo del método PUT
      # Asegúrate de que la solicitud tiene el tipo de contenido correcto
    if request.content_type != 'application/json':
        return jsonify({'error': 'Tipo de contenido no soportado, se esperaba application/json'}), 415
    

    encargado = Encargado.query.get(id)

    if not encargado:
        return jsonify({'error': 'Empleado no encontrado'}), 404

    # Manejo de la solicitud
    data = request.json
    encargado.nombre = data['nombre']
    encargado.puesto = data['puesto']
    encargado.num_empleado = data['num_empleado']
    encargado.evaluador_id = data['evaluador_id']
    encargado.id = data['id']
    db.session.commit()
        
    return jsonify({'message': 'Encargado editado correctamente'}), 200


# CREACION NUEVO EMPLEADO --------------------------------------------------------------------------------------------

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
    rol_id = data.get('rol_id', 3)

    if not nombre or not puesto or not num_empleado:
        return jsonify({'error': 'Faltan datos'}), 400

    try:
        nuevo_empleado = Empleado(
            nombre=nombre,
            puesto=puesto,
            num_empleado=num_empleado,
            evaluador_id=evaluador_id,
            rol_id=rol_id
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
                'evaluador': nuevo_empleado.evaluador_id,
                'rol': nuevo_empleado.rol_id
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error':'Error al crear el empleado', 'mensaje': str(e)}), 500


@routes_blueprint.route('/encargados/nuevo/<int:id>', methods=['OPTIONS', 'POST'])
def nuevo_encargado(id):
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({'error': 'Encargado especial no encontrado'}), 404


    data = request.get_json()
    if not data:
        return jsonify({'error': 'No se recibio datos'}), 400

    nombre = data.get('nombre')
    puesto = data.get('puesto')
    num_empleado = data.get('num_empleado')
    evaluador_id = data.get('evaluador_id')
    rol_id = data.get('rol_id',2)

    if not nombre or not puesto or not num_empleado:
        return jsonify({'error': 'Faltan datos'}), 400

    try:
        nuevo_encargado = Encargado(
            nombre=nombre,
            puesto=puesto,
            num_empleado=num_empleado,
            evaluador_id=evaluador_id,
            rol_id=rol_id
        )
        db.session.add(nuevo_encargado)
        db.session.commit()

        return jsonify({
            'message': 'Encargado creado correctamente',
            'encargado': {
                'id': nuevo_encargado.id,
                'nombre': nuevo_encargado.nombre,
                'puesto': nuevo_encargado.puesto,
                'num_empleado': nuevo_encargado.num_empleado,
                'evaluador': nuevo_encargado.evaluador_id,
                'rol': nuevo_encargado.rol_id
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error':'Error al crear el encargado', 'mensaje': str(e)}), 500



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



