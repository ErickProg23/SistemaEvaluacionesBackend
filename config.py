class Config:
    # Configuración de la base de datos MySQL
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://develop:admin123@localhost/evaluaciones'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'pruebas2025'
