import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from app import create_app
from app.services.evaluaciones_service import detectar_evaluaciones_atrasadas

def main():
    app = create_app()
    with app.app_context():
        nuevos, anio, mes = detectar_evaluaciones_atrasadas()
        print({"nuevos": nuevos, "anio": anio, "mes": mes})

if __name__ == "__main__":
    main()