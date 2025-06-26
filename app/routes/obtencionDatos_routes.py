from flask import Blueprint, request, jsonify
from app.models import Empleado, Encargado, Usuario


# Definición del Blueprint para las rutas de obtención de datos
datos_bp = Blueprint('datos_bp', __name__)



#OBTENER DATOS --------------------------------------------------------------------------------------------

@datos_bp.route('/usuarios/empleados', methods=['GET'])
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


@datos_bp.route('/usuarios/encargados', methods=['GET'])
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

@datos_bp.route('/usuarios/empleados-por-usuario/<int:usuario_id>', methods=['GET'])
def obtener_empleados_por_usuario(usuario_id):
    try:
        # Verificar que el usuario exista
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify([]), 200

        # Obtener los encargados relacionados a este usuario desde encargado_usuario
        encargados = usuario.encargados_relacionados

        if not encargados:
            return jsonify([]), 200

        # Crear la lista de encargados
        encargados_data = [
            {
                'id': encargado.id,
                'nombre': encargado.nombre,
                'puesto': encargado.puesto,
                'num_empleado': encargado.num_empleado,
                'tipo_evaluacion': encargado.tipo_evaluacion,
                'activo': encargado.activo
            }
            for encargado in encargados
        ]

        return jsonify(encargados_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@datos_bp.route('/usuarios/empleados/<int:encargado_id>', methods=['GET'])
def obtener_empleados_por_encargado(encargado_id):
    try:
        # Consultar empleados asociados al encargado específico
        empleados = Empleado.query.filter(
            Empleado.activo == True,  # Solo empleados activos
            Empleado.encargados.any(id=encargado_id)
            ).all()

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

@datos_bp.route('/usuarios/empleados-por-usuario/<int:usuario_id>', methods=['GET'])
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


@datos_bp.route('/usuarios/mayores', methods=['GET'])
def get_mayores():
    usuarios = Usuario.query.filter_by(rol_id=4).all()

    if usuarios:
        usuarios_data = [{'id': usuario.id, 'nombre': usuario.nombre, 'activo': usuario.activo} 
        for usuario in  usuarios]
        return jsonify(usuarios_data), 200
    else:
        return jsonify({'message': 'No se pudo extraer la informacion'}), 401


        
@datos_bp.route('/usuarios/empleado/<int:id>', methods=['GET'])
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


@datos_bp.route('/usuarios/encargado/<int:id>', methods=['GET'])
def obtener_encargado(id):
    # Obtiene al empleado con su evaluador
    encargado = Encargado.query.filter_by(id=id).first()

    if encargado:
        # Construcción del resultado con la información del evaluador
        encargados_usuarios = []
        for usuario in encargado.usuarios:
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