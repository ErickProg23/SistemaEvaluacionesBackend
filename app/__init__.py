from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from config import Config
from flask_cors import CORS

# Inicialización de las extensiones
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # Cargar la configuración desde el archivo config.py

    # Habilitar CORS para todas las rutas
    CORS(app)

    # Inicializar las extensiones
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # Importar las rutas y modelos para inicializarlos
    with app.app_context():
        from . import models  # Esto importa y crea las tablas en la base de datos
        from .routes import routes_blueprint  # Importar el Blueprint definido en routes.py
        # Registrar el Blueprint
        app.register_blueprint(routes_blueprint, url_prefix='/api')
    
    return app
