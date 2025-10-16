from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app.models import Usuario, Encargado, EvaluacionTemporal
from datetime import datetime
import datetime as dt
from app import db

# Definición del Blueprint para las rutas de login
login_bp = Blueprint('login_bp', __name__)

#LOGIN --------------------------------------------------------------------------------------------
@login_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    usuario = data.get('usuario')
    contrasena = data.get('contrasena')
    nombre = data.get('nombre')

    # Busca al usuario en la base de datos
    usuario = Usuario.query.filter_by(usuario=usuario).first()

    # Verificar si el usuario existe y la contraseña es correcta
    if contrasena and usuario and usuario.contrasena == contrasena:
        # Verificar si la cuenta está activa
        if not usuario.activo:
            return jsonify({'message': 'Cuenta desactivada. Contacte al administrador.'}), 403
            
        # Generar un token de acceso
        access_token = create_access_token(identity={'usuario': usuario.usuario})

        # Recupera el rol_id del usuario
        rol_id = usuario.rol_id  # Asegúrate de que `Usuario` tiene una columna llamada `rol_id`

        # Busca si el usuario tiene un registro en la tabla encargado
        encargado = Encargado.query.filter_by(usuario_id=usuario.id).first()

        # Si el encargado existe, obtenemos su ID y tipo_evaluacion, sino usamos null o un identificador especial
        id_encargado = encargado.id if encargado else None

        puesto_encargado = encargado.puesto if encargado else None

        # 👇 Lógica para eliminar evaluaciones temporales caducadas
        if id_encargado:
            semana_actual = datetime.now().isocalendar()[1]
            semana_anterior = semana_actual - 1 if semana_actual > 1 else 52  # Manejo del caso de la semana 1

            evaluaciones = EvaluacionTemporal.query.filter_by(id_encargado=id_encargado).all()

            for eval in evaluaciones:
                if eval.num_semana < semana_anterior:
                    db.session.delete(eval)

            db.session.commit()

        tipo_evaluacion = encargado.tipo_evaluacion if encargado else None
        
        # Guardar el ID del usuario en una variable separada
        usuario_id = usuario.id

        nombre = usuario.nombre
        
        return jsonify({'access_token': access_token}
        , {'rol_id': rol_id}
        , {'nombre': nombre},
        {'id_encargado': id_encargado},
        {'usuario_id': usuario_id},
        {'tipo_evaluacion': tipo_evaluacion},
        {'puesto_encargado': puesto_encargado}), 200

    return jsonify({'message': 'Usuario o contraseña incorrectos'}), 401