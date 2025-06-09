from flask import Blueprint, request, jsonify
from app.models import Empleado, Encargado, Usuario, Pregunta
from app import db


# Definición del Blueprint para las rutas de obtención de datos
preguntas_bp = Blueprint('preguntas_bp', __name__)



@preguntas_bp.route('/preguntas/evaluacion', methods=['GET'])
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

@preguntas_bp.route('/preguntas', methods=['GET'])
def obtener_Todaspreguntas():
    # Obtener todas las preguntas sin filtrar por tipo
    preguntas = Pregunta.query.all()

    if not preguntas:
        return jsonify({"mensaje": "No hay preguntas disponibles"}), 404

    preguntas_json = [pregunta.to_dict() for pregunta in preguntas]
    return jsonify(preguntas_json), 200


# Crear nueva pregunta
@preguntas_bp.route('/newPregunta', methods=['OPTIONS', 'POST'])
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
@preguntas_bp.route('/preguntas/<int:id>', methods=['OPTIONS', 'PUT'])
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