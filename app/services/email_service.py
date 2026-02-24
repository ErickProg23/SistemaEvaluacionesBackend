# services/email_service.py

from app.models import Encargado, Usuario
from app.utils import enviar_correo

def enviar_correo_atrasos(ids_encargados, anio, mes):
    encargados = Encargado.query.filter(Encargado.id.in_(ids_encargados)).all()

    usuarios = []
    for enc in encargados:
        if enc.usuario_id:
            u = Usuario.query.get(enc.usuario_id)
            if u:
                usuarios.append(u)

    destinatarios = [u.correo for u in usuarios if u.correo]

    def correo_de(enc):
        for u in usuarios:
            if u.id == enc.usuario_id and u.correo:
                return u.correo
        return 'sin correo'

    lista = "\n".join(f"- {enc.nombre} ({correo_de(enc)})" for enc in encargados)

    cuerpo = f"""
Los siguientes encargados no realizaron la evaluación correspondiente.

Periodo: {mes}/{anio}

Encargados:
{lista}
"""

    asunto = f"Evaluaciones atrasadas {mes}/{anio}"
    if destinatarios:
        enviar_correo(destinatarios, asunto, cuerpo)
    else:
        print(cuerpo)  # temporal
