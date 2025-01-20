from app import create_app, db
from app.models import *  # Importamos el modelo

# Crear la aplicación Flask
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)