from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from app.config import Config
from flask_cors import CORS
from flask_mail import Mail

# Inicialización de las extensiones
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # Cargar la configuración desde el archivo config.py

    # Habilitar CORS para todas las rutas
    CORS(app)

    # Inicializar las extensiones
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)

    # Importar las rutas y modelos para inicializarlos
    with app.app_context():
        from . import models  # Esto importa y crea las tablas en la base de datos
        from .routes.usuarios_routes import user_bp
        from .routes.login_routes import login_bp
        from .routes.obtencionDatos_routes import datos_bp
        from .routes.preguntas_routes import preguntas_bp
        from .routes.actualizacionDatos_routes import act_bp
        from .routes.creacion_routes import creacion_bp
        from .routes.evaluaciones_routes import evaluacion_bp
        from .routes.notificaciones_routes import notis_bp
        from .routes.formato_routes import formato_bp
        from .routes.promedio_routes import prom_bp
        from .routes.ticket_routes import tickets_bp
        from .routes.retroalimentacion_routes import retroalimentacion_bp
        from .routes.uploads_routes import uploads_bp
        from .routes.roles_routes import roles_bp
        from .main_routes import routes_blueprint  # Importar el Blueprint definido en routes.py


        # Registrar el Blueprint
        app.register_blueprint(user_bp, url_prefix='/api/users')
        app.register_blueprint(login_bp, url_prefix='/api/login')  # Registrar el Blueprint de login
        app.register_blueprint(datos_bp, url_prefix='/api/datos')  # Registrar el Blueprint de obtención de datos
        app.register_blueprint(preguntas_bp, url_prefix='/api/preguntas')  # Registrar el Blueprint de preguntas
        app.register_blueprint(act_bp, url_prefix='/api/actualizacion')  # Registrar el Blueprint de actualización de datos
        app.register_blueprint(creacion_bp, url_prefix='/api/creacion')
        app.register_blueprint(evaluacion_bp, url_prefix='/api/evaluacion')
        app.register_blueprint(notis_bp, url_prefix='/api/notificaciones')  # Registrar el Blueprint de notificaciones
        app.register_blueprint(formato_bp, url_prefix='/api/formatos')  # Registrar el Blueprint de formatos
        app.register_blueprint(prom_bp, url_prefix='/api/promedio')
        app.register_blueprint(tickets_bp, url_prefix='/api/tickets')  # Registrar el Blueprint principal
        app.register_blueprint(retroalimentacion_bp, url_prefix='/api/retroalimentacion')  # Registrar el Blueprint de retroalimentación
        app.register_blueprint(roles_bp, url_prefix='/api/roles')  # Registrar el Blueprint de roles
        app.register_blueprint(routes_blueprint, url_prefix='/api')
        app.register_blueprint(uploads_bp, url_prefix='/uploads')
    
    return app
