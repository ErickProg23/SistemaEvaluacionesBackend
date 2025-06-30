from datetime import datetime
from flask import Blueprint, request, jsonify
from app.models import Empleado, Encargado, Notificacion, Usuario
from app import db


# Definición del Blueprint para las rutas de obtención de datos
act_bp = Blueprint('act_bp', __name__)



@act_bp.route('/usuarios/empleados/desactivar/<int:id>', methods=['OPTIONS', 'PUT'])
def deactivate_employee(id):  
    if request.method == 'OPTIONS':
        # Respuesta preflight CORS
        return '', 200


    # Manejo del método PUT
    empleado = Empleado.query.get(id)
    if not empleado:
        return jsonify({'error': 'Empleado no encontrado'}), 404
    
    try:
        empleado.activo = False

        for encargado in list(empleado.encargados):
            empleado.encargados.remove(encargado)


        db.session.commit()

        return jsonify({'message': 'Empleado desactivado correctamente'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@act_bp.route('/usuarios/encargados/desactivar/<int:id>', methods=['OPTIONS', 'PUT'])
def deactivate_encargado(id):    
    # Manejo del método PUT
    encargado = Encargado.query.get(id)
    if not encargado:
        return jsonify({'error': 'Encargado no encontrado'}), 404
    
    encargado.activo = False
    db.session.commit()
    return jsonify({'message': 'Encargado desactivado correctamente'})

@act_bp.route('/usuarios/encargados/activar/<int:id>', methods=['OPTIONS', 'PUT'])
def activate_encargado(id):    
    # Manejo del método PUT
    encargado = Encargado.query.get(id)
    if not encargado:
        return jsonify({'error': 'Encargado no encontrado'}), 404
    
    encargado.activo = True
    db.session.commit()
    return jsonify({'message': 'Encargado activado correctamente'})


@act_bp.route('/usuarios/empleados/activar/<int:id>', methods=['OPTIONS', 'PUT'])
def activate_empleado(id):    
    # Manejo del método PUT
    empleado = Empleado.query.get(id)
    if not empleado:
        return jsonify({'error': 'Empledado no encontrado'}), 404
    
    empleado.activo = True
    db.session.commit()
    return jsonify({'message': 'Empleado activado correctamente'})

@act_bp.route('/empleado/editar/<int:id>', methods =['PUT'])
def editar_empleado(id):
    # Manejo del método PUT
      # Asegúrate de que la solicitud tiene el tipo de contenido correcto
    if request.content_type != 'application/json':
        return jsonify({'error': 'Tipo de contenido no soportado, se esperaba application/json'}), 415
    

    try:
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

            encargados_a_eliminar = encargados_actuales_ids - nuevos_encargados_ids
            encargados_a_agregar = nuevos_encargados_ids - encargados_actuales_ids

            # Eliminar encargados
            for encargado in list(empleado.encargados):
                if encargado.id in encargados_a_eliminar:
                    empleado.encargados.remove(encargado)

            # Agregar encargados nuevos
            encargados = Encargado.query.filter(Encargado.id.in_(encargados_a_agregar)).all()
            if len(encargados) != len(encargados_a_agregar):
                return jsonify({'error': 'Uno o más encargados no fueron encontrados'}), 404
            for encargado in encargados:
                empleado.encargados.append(encargado)

            # Crear notificaciones
            fecha_actual = datetime.utcnow()
            for id_baja in encargados_a_eliminar:
                notificacion = Notificacion(
                    id_encargado=id_baja,
                    id_empleado=empleado.id,
                    accion="2",
                    fecha=fecha_actual
                )
                db.session.add(notificacion)

            for id_alta in encargados_a_agregar:
                notificacion = Notificacion(
                    id_encargado=id_alta,
                    id_empleado=empleado.id,
                    accion="1",
                    fecha=fecha_actual
                )
                db.session.add(notificacion)

            db.session.commit()
            return jsonify({'message': 'Empleado editado correctamente'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    


@act_bp.route('/encargado/editar/<int:id>', methods =['PUT'])
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