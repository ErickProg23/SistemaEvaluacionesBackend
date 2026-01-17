# services/email_service.py

from app.models import Encargado

def enviar_correo_atrasos(ids_encargados, anio, mes):
    encargados = Encargado.query.filter(
        Encargado.id.in_(ids_encargados)
    ).all()

    lista = "\n".join(
        f"- {e.nombre} ({e.email})" for e in encargados
    )

    cuerpo = f"""
Los siguientes encargados no realizaron la evaluación correspondiente.

Periodo: {mes}/{anio}

Encargados:
{lista}
"""

    # Aquí va tu lógica real de envío
    print(cuerpo)  # temporal
