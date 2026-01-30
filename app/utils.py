import os
from flask import current_app
from flask_mail import Message
from app import mail

def enviar_correo(destinatario, asunto, mensaje, cc=None, bcc=None, mensaje_html=None):
    # ... existing code ...
    try:
        recipients = destinatario if isinstance(destinatario, list) else [destinatario]
        msg = Message(asunto, recipients=recipients)
        if cc:
            msg.cc = cc if isinstance(cc, list) else [cc]
        if bcc:
            msg.bcc = bcc if isinstance(bcc, list) else [bcc]
        msg.body = mensaje
        if mensaje_html:
            msg.html = mensaje_html
        mail.send(msg)
        print("✅ Correo enviado correctamente a", recipients)
    except Exception as e:
        print("❌ Error al enviar correo:", e)