from flask import Blueprint, request, jsonify
from app.models import Empleado, Encargado, Usuario
from app import db


# Definición del Blueprint para las rutas de obtención de datos
creacion_bp = Blueprint('creacion_bp', __name__)


# CREACION NUEVO EMPLEADO Y ENCARGADO --------------------------------------------------------------------------------------------
@creacion_bp.route('/empleados/nuevo', methods=['OPTIONS', 'POST'])
def new_employee():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No se recibio datos'}), 400

    nombre = ' '.join(((data.get('nombre') or '').strip()).split())
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


@creacion_bp.route('/encargados/nuevo', methods=['OPTIONS', 'POST'])
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

            nuevo_encargado.usuarios.extend(encargados)  # Asignar la relación muchos a muchos

        db.session.commit()

        return jsonify({
            'message': 'Encargado creado correctamente',
            'encargado': {
                'id': nuevo_encargado.id,
                'nombre': nuevo_encargado.nombre,
                'usuario_id': nuevo_encargado.usuario_id,
                'puesto': nuevo_encargado.puesto,
                'encargados': [{'id': e.id, 'nombre': e.nombre} for e in nuevo_encargado.usuarios],  # Mostrar los evaluadores
                'num_empleado': nuevo_encargado.num_empleado,
                'rol': nuevo_encargado.rol_id
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error al crear el encargado', 'mensaje': str(e)}), 500