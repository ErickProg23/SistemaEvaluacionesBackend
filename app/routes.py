from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from .models import Usuario, Rol, Empleado, Encargado, Pregunta, Evaluacion, Notificacion
from flask_cors import CORS
from app import db
from collections import defaultdict
from datetime import datetime, timedelta
from sqlalchemy import func, update
import pytz
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

    nombre = data.get('nombre').strip().lower()  # Convertir a minúsculas y quitar espacios
    puesto = data.get('puesto')
    num_empleado = data.get('num_empleado')
    encargados_ids = data.get('encargados_ids', [])
    rol_id = data.get('rol_id',2)

    if not nombre or not puesto or not num_empleado:
        return jsonify({'error': 'Faltan datos'}), 400

    try:
        # Paso 1: Buscar el usuario por nombre
        usuario = Usuario.query.filter(Usuario.nombre.collate('utf8mb4_general_ci') == nombre).first()
        if not usuario:
            return jsonify({'error': f'No existe un usuario con el nombre "{nombre}"'}), 404

        nuevo_encargado = Encargado(
            nombre=nombre,
            puesto=puesto,
            num_empleado=num_empleado,
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
        # Obtener los datos del payload y el id_encargado desde el cuerpo de la solicitud
        data = request.json
        payload = data.get('payload')
        id_encargado = data.get('idEncargado')

        # Validar que los datos necesarios estén presentes
        if not payload or not id_encargado:
            return jsonify({'error': 'Datos incompletos'}), 400

        # Procesar cada evaluación en el payload
        for evaluacion_data in payload:
            empleado_id = evaluacion_data.get('empleado_id')
            calificaciones = evaluacion_data.get('calificaciones')
            comentarios = evaluacion_data.get('comentarios')
            ausente = evaluacion_data.get('ausente', False)  # Valor por defecto: False

            # Convertir comentarios a cadena si es una lista
            if isinstance(comentarios, list):
                comentarios = ', '.join(comentarios)  # Une los elementos de la lista en una cadena

            # Convertir el valor de 'ausente' a 1 (true) o 0 (false)
            ausente_db = 1 if ausente else 0

            # Obtener los aspectos (preguntas) desde la base de datos
            aspectos_db = Pregunta.query.all()

            # Procesar cada aspecto (pregunta)
            for aspecto_db in aspectos_db:
                calificacion = calificaciones.get(aspecto_db.texto, 0)  # Obtener la calificación del aspecto
                porcentaje = calificacion * aspecto_db.peso  # Calcular el porcentaje ponderado

                # Crear una nueva evaluación para cada aspecto
                nueva_evaluacion = Evaluacion(
                    empleado_id=empleado_id,
                    encargado_id=id_encargado,
                    fecha_evaluacion=datetime.now(),
                    aspecto=aspecto_db.texto,  # Nombre del aspecto
                    total_puntos=calificacion,  # Calificación del aspecto
                    porcentaje_total=porcentaje,  # Porcentaje ponderado
                    comentarios=comentarios,  # Comentarios generales
                    ausente=ausente_db  # Guardar 1 si está ausente, 0 si no
                )

                # Guardar en la base de datos
                db.session.add(nueva_evaluacion)

        # Confirmar los cambios en la base de datos
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
@routes_blueprint.route('/evaluaciones/todas', methods=['OPTIONS','GET'])
def obtener_evaluaciones_todas():
    try: 
        # 1. Obtener el mes más reciente (incluyendo evaluaciones ausentes)
        fecha_reciente = db.session.query(
            db.func.max(db.func.date_format(Evaluacion.fecha_evaluacion, '%Y-%m'))
        ).scalar()  # ¡Sin filtrar por ausente!

        if not fecha_reciente:
            return jsonify({'error': 'No hay evaluaciones'}), 404

        # 2. Obtener TODAS las evaluaciones del mes (ausentes y no ausentes)
        evaluaciones = Evaluacion.query.filter(
            db.func.date_format(Evaluacion.fecha_evaluacion, '%Y-%m') == fecha_reciente
        ).all()

        # 3. Separar evaluaciones válidas y ausentes
        evaluaciones_validas = [e for e in evaluaciones if e.ausente == 0]
        evaluaciones_ausentes = [e for e in evaluaciones if e.ausente == 1]

        # 4. Procesar solo las evaluaciones válidas para cálculos
        resultados = defaultdict(lambda: {
            'semanas': defaultdict(lambda: {'suma_aspectos': 0.0}),
            'nombre': 'Nombre no encontrado',
            'promedio_mensual': 0.0,
            'ausente': False  # Indica si el empleado tiene solo evaluaciones ausentes
        })

        empleado_ids = {eval.empleado_id for eval in evaluaciones}  # Incluye todos los empleados
        empleados_dict = {emp.id: emp.nombre for emp in Empleado.query.filter(Empleado.id.in_(empleado_ids)).all()}

        # Procesar evaluaciones válidas
        for eval in evaluaciones_validas:
            empleado_id = eval.empleado_id
            semana = eval.fecha_evaluacion.isocalendar().week
            resultados[empleado_id]['semanas'][semana]['suma_aspectos'] += float(eval.porcentaje_total)
            resultados[empleado_id]['nombre'] = empleados_dict.get(empleado_id, 'Nombre no encontrado')

        # Procesar evaluaciones ausentes (solo para incluir en la respuesta)
        for eval in evaluaciones_ausentes:
            empleado_id = eval.empleado_id
            if empleado_id not in resultados:
                resultados[empleado_id]['nombre'] = empleados_dict.get(empleado_id, 'Nombre no encontrado')
                resultados[empleado_id]['ausente'] = True  # Marcar como ausente

        # 5. Calcular promedios mensuales (solo para evaluaciones válidas)
        for empleado_id, datos in resultados.items():
            if datos['ausente']:
                continue  # No calcular promedio si solo tiene evaluaciones ausentes

            porcentajes_semanales = []
            for semana, valores in datos['semanas'].items():
                suma_aspectos = valores['suma_aspectos']
                porcentaje_semanal = (suma_aspectos / 500) * 100
                porcentajes_semanales.append(porcentaje_semanal)
            
            if porcentajes_semanales:
                datos['promedio_mensual'] = sum(porcentajes_semanales) / len(porcentajes_semanales)
                datos['promedio_mensual'] = min(datos['promedio_mensual'], 100.0)

        # 6. Preparar respuesta con TODAS las evaluaciones
        response_data = {
            'evaluaciones': [
                {
                    'id': eval.id,
                    'empleado_id': eval.empleado_id,
                    'fecha': eval.fecha_evaluacion.isoformat(),
                    'porcentaje_total': float(eval.porcentaje_total),
                    'ausente': bool(eval.ausente)  # Campo clave para el frontend
                }
                for eval in evaluaciones  # Incluye todas
            ],
            'resultados': [
                {
                    'empleado_id': emp_id,
                    'nombre': datos['nombre'],
                    'promedio_mensual': round(datos['promedio_mensual'], 2) if not datos['ausente'] else None,
                    'ausente': datos['ausente']
                }
                for emp_id, datos in resultados.items()
            ]
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_blueprint.route('/evaluaciones', methods=['OPTIONS','GET'])
def obtener_evaluaciones():
    #Validar parametros
    encargado_id = request.args.get('encargado_id')
    if not encargado_id:
        return jsonify({'error': 'Se requiere ID de encargado'}), 400

    try:
        #1. Determinar el mes mas reciente con evaluaciones
        fecha_reciente = db.session.query(
            db.func.max(
                db.case(
                    (Evaluacion.encargado_id == encargado_id, db.func.date_format(Evaluacion.fecha_evaluacion, '%Y-%m')),
                    else_=None
                )
            )
        ).scalar()

        if not fecha_reciente:
            return jsonify({'error': 'No hay evaluaciones'}), 404

        # 2. Obtener todas las evaluaciones del mes mas reciente 
        evaluaciones = db.session.query(Evaluacion).filter(
            Evaluacion.encargado_id == encargado_id,
            db.func.date_format(Evaluacion.fecha_evaluacion, '%Y-%m') == fecha_reciente
        ).all()

        # Obtener IDs de empleados únicos
        empleado_ids = {eval.empleado_id for eval in evaluaciones}

        # 3. Consultar nombres de empleados
        empleados = db.session.query(Empleado.id, Empleado.nombre).filter(
            Empleado.id.in_(empleado_ids)
        ).all()
        empleados_dict = {emp.id: emp.nombre for emp in empleados}

        # 4. Procesar datos
        resultados = defaultdict(lambda: {
            'suma_porcentaje_total': 0.0,
            'porcentaje_final': 0.0,
            'nombre': 'Nombre no encontrado'
        })

        for eval in evaluaciones:
            empleado_id = eval.empleado_id
            resultados[empleado_id]['suma_porcentaje_total'] += float(eval.porcentaje_total)
            resultados[empleado_id]['nombre'] = empleados_dict.get(empleado_id, 'Nombre no encontrado')

        # Calcular porcentaje_final
        for empleado_id, datos in resultados.items():
            suma_porcentaje_total = datos['suma_porcentaje_total']
            datos['porcentaje_final'] = (suma_porcentaje_total / 500) * 100
            datos['porcentaje_final'] = min(datos['porcentaje_final'], 100.0)



         # 5. Calcular promedios 
        promedios = [min(datos['porcentaje_final'], 100.0) for datos in resultados.values()]
        promedio_general = sum(promedios) / len(promedios) if promedios else 0

        # 6. Formatear respuesta
        from dateutil.relativedelta import relativedelta

        fecha_inicio = datetime.strptime(fecha_reciente, '%Y-%m')
        fecha_fin = fecha_inicio + relativedelta(months=1, days=-1)  # Último día del mes


        return jsonify({
            'promedio_general': round(promedio_general, 2),
            'total_empleados': len(promedios),
            'periodo':{
                'inicio': fecha_inicio,
                'fin': fecha_fin
            },
            'detalle_empleados':[
                {
                    'nombre': datos['nombre'],
                    'empleado_id': emp_id,
                    'calificacion_final': round(datos['porcentaje_final'], 2),
                } for emp_id, datos in resultados.items()
            ]
            }), 200

    except Exception as e:
        return jsonify({'error': str(e)}),500
