from app.models import Empleado, Encargado, Formato, HabitacionesInspecciones, Usuario
from flask import Blueprint, make_response, request, jsonify
from app import db
from app.utils import enviar_correo
from datetime import datetime
from sqlalchemy import func
import html

# Definición del Blueprint para las rutas de obtención de datos
habitacionesInspecciones_bp = Blueprint('habitacionesInspecciones_bp', __name__)

SISTEMAS_FIELDS = {'control_tv', 'telefono', 'roku'}
LLAVES_FIELDS = {'toallas', 'botella_vidrio'}
TRACKED_FIELDS = SISTEMAS_FIELDS | LLAVES_FIELDS

def correo_encargado_por_puesto(texto_puesto):
    enc = Encargado.query.filter(
        Encargado.activo == True,
        func.lower(Encargado.puesto).like(f"%{texto_puesto.lower()}%")
    ).first()

    if not enc or not enc.usuario_id:
        return ''

    u = Usuario.query.get(enc.usuario_id)
    return (u.correo or '').strip() if u and u.correo else ''

def build_inspeccion_email_html(titulo, room, cuando, quien_label, detalles):
    titulo_e = html.escape(str(titulo or 'Inspección'))
    room_e = html.escape(str(room))
    cuando_e = html.escape(str(cuando))
    quien_e = html.escape(str(quien_label or ''))

    items = ''.join(f"<li style='margin:4px 0'>{html.escape(str(d))}</li>" for d in (detalles or []))

    return f"""<!doctype html>
<html>
  <body style=\"margin:0;padding:0;background:#f6f8fb;font-family:Arial,Helvetica,sans-serif;\">
    <div style=\"max-width:640px;margin:0 auto;padding:20px;\">
      <div style=\"background:#0f172a;color:#fff;padding:16px 18px;border-radius:10px 10px 0 0;\">
        <div style=\"font-size:16px;font-weight:700;\">{titulo_e}</div>
        <div style=\"font-size:12px;opacity:.9;margin-top:4px;\">Habitación {room_e}</div>
      </div>

      <div style=\"background:#ffffff;border:1px solid #e5e7eb;border-top:0;padding:16px 18px;border-radius:0 0 10px 10px;\">
        <div style=\"font-size:13px;color:#334155;\">Se detectaron detalles en la habitacion durante la inspección.</div>

        <table style=\"width:100%;border-collapse:collapse;margin-top:14px;font-size:13px;\">
          <tr>
            <td style=\"padding:6px 0;color:#64748b;width:120px;\">Fecha:</td>
            <td style=\"padding:6px 0;color:#0f172a;\">{cuando_e}</td>
          </tr>
          <tr>
            <td style=\"padding:6px 0;color:#64748b;\">Actualizó:</td>
            <td style=\"padding:6px 0;color:#0f172a;\">{quien_e}</td>
          </tr>
        </table>

        <div style=\"margin-top:14px;font-size:13px;font-weight:700;color:#0f172a;\">Detalles detectados</div>
        <ul style=\"margin:8px 0 0 18px;padding:0;color:#0f172a;font-size:13px;\">{items}</ul>

        <div style=\"margin-top:16px;font-size:11px;color:#64748b;\">Mensaje generado automáticamente.</div>
      </div>
    </div>
  </body>
</html>"""

@habitacionesInspecciones_bp.route('/crear_habitacion_inspeccion', methods=['OPTIONS','POST'])
def crear_habitacion_inspeccion():

    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json(silent=True) or {}
    except Exception as e:
        return jsonify({'error': f'Error al procesar los datos: {str(e)}'}), 400

    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'Faltan datos requeridos (user_id)'}), 400

    room_id = data.get('room_id')
    if room_id is None:
        room_id = data.get('numero')

    if room_id is None:
        return jsonify({'error': 'Faltan datos requeridos (room_id)'}), 400

    habitacion_existente = HabitacionesInspecciones.query.filter_by(room_id=room_id).first()
    if habitacion_existente:
        return jsonify({'error': 'La habitación ya existe'}), 400

    nueva_habitacion = HabitacionesInspecciones(
        room_id=room_id,
        user_id=user_id,
        control_tv=data.get('control_tv', False),
        telefono=data.get('telefono', False),
        roku=data.get('roku', False),
        toallas=data.get('toallas', False),
        botella_vidrio=data.get('botella_vidrio', False),
        notes=data.get('notes', None),
    )

    try:
        db.session.add(nueva_habitacion)
        db.session.commit()
        return jsonify({'message': 'Habitación creada exitosamente'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al guardar la habitación: {str(e)}'}), 500

@habitacionesInspecciones_bp.route('/actualizar_habitacion_inspeccion', methods=['OPTIONS','PUT'])
def actualizar_habitacion_inspeccion():

    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json(silent=True) or {}
    except Exception as e:
        return jsonify({'error': f'Error al procesar los datos: {str(e)}'}), 400

    room_id = data.get('room_id')
    if room_id is None:
        room_id = data.get('numero')

    if room_id is None:
        return jsonify({'error': 'Faltan datos requeridos (room_id)'}), 400

    habitacion = HabitacionesInspecciones.query.filter_by(room_id=room_id).first()
    if not habitacion:
        return jsonify({'error': 'Habitación no encontrada'}), 404

    def parse_bool(v):
        if v is None:
            return None
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(int(v))
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ('1', 'true', 't', 'yes', 'y', 'si', 'sí'):
                return True
            if s in ('0', 'false', 'f', 'no', 'n'):
                return False
        return bool(v)

    updatable_keys = {'user_id', 'control_tv', 'telefono', 'roku', 'toallas', 'botella_vidrio', 'notes'}
    if not any(k in data for k in updatable_keys):
        return jsonify({'error': 'No se proporcionaron campos para actualizar'}), 400

    before = {f: getattr(habitacion, f) for f in TRACKED_FIELDS}

    to_notify_sistemas = []
    to_notify_llaves = []

    if 'user_id' in data and data.get('user_id') is not None:
        habitacion.user_id = data.get('user_id')

    for field in ['control_tv', 'telefono', 'roku', 'toallas', 'botella_vidrio']:
        if field not in data:
            continue

        parsed = parse_bool(data.get(field))
        if parsed is None:
            continue

        old_value = before.get(field)
        if old_value is True and parsed is False:
            if field in SISTEMAS_FIELDS:
                to_notify_sistemas.append(field)
            elif field in LLAVES_FIELDS:
                to_notify_llaves.append(field)

        setattr(habitacion, field, parsed)

    if 'notes' in data:
        habitacion.notes = data.get('notes')

    try:
        db.session.commit()

        labels = {
            'control_tv': 'Control TV',
            'telefono': 'Teléfono',
            'roku': 'Roku',
            'toallas': 'Toallas',
            'botella_vidrio': 'Botella de vidrio',
        }

        frases_no = {
            'control_tv': 'La habitación no tiene control de TV.',
            'telefono': 'El teléfono no funciona / no está disponible.',
            'roku': 'La habitación no tiene Roku.',
            'toallas': 'La habitación no tiene toallas.',
            'botella_vidrio': 'La habitación no tiene botella de vidrio.',
        }

        def fmt_detalles(campos):
            return "\n".join(f"- {frases_no.get(c, f'La habitación no tiene {labels.get(c, c)}.')}" for c in campos)

        room = habitacion.room_id
        quien_id = habitacion.user_id
        cuando = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        usuario_actualizo = Usuario.query.get(quien_id) if quien_id is not None else None
        quien_nombre = (usuario_actualizo.nombre if usuario_actualizo and usuario_actualizo.nombre else None)
        quien_label = quien_nombre or f"user_id: {quien_id}"

        if to_notify_sistemas:
            destinatario_sistemas = correo_encargado_por_puesto('sistemas')
            if destinatario_sistemas:
                asunto = f"Inspección Habitación {room} - Revisión de Sistemas"
                mensaje = (
                    f"En la habitación {room} se detectaron los siguientes detalles:\n\n"
                    f"Fecha: {cuando}\n"
                    f"Actualizó: {quien_label}\n\n"
                    f"Detalles:\n{fmt_detalles(to_notify_sistemas)}\n"
                )
                detalles = [frases_no.get(c, f"La habitación no tiene {labels.get(c, c)}.") for c in to_notify_sistemas]
                mensaje_html = build_inspeccion_email_html(
                    titulo="Inspección - Revisión de Sistemas",
                    room=room,
                    cuando=cuando,
                    quien_label=quien_label,
                    detalles=detalles
                )
                try:
                    enviar_correo(destinatario_sistemas, asunto, mensaje, mensaje_html=mensaje_html)
                except Exception as e:
                    print(f"Error al enviar correo a sistemas: {e}")
            else:
                print("No se encontró correo para el encargado de sistemas")

        if to_notify_llaves:
            destinatario_llaves = correo_encargado_por_puesto('ama de llaves')
            if destinatario_llaves:
                asunto = f"Inspección Habitación {room} - Revisión"
                mensaje = (
                    f"En la habitación {room} se detectaron los siguientes detalles (cambios de Sí a No):\n\n"
                    f"Fecha: {cuando}\n"
                    f"Actualizó: {quien_label}\n\n"
                    f"Detalles:\n{fmt_detalles(to_notify_llaves)}\n"
                )
                detalles = [frases_no.get(c, f"La habitación no tiene {labels.get(c, c)}.") for c in to_notify_llaves]
                mensaje_html = build_inspeccion_email_html(
                    titulo="Inspección - Revisión",
                    room=room,
                    cuando=cuando,
                    quien_label=quien_label,
                    detalles=detalles
                )
                try:
                    enviar_correo(destinatario_llaves, asunto, mensaje, mensaje_html=mensaje_html)
                except Exception as e:
                    print(f"Error al enviar correo a llaves: {e}")
            else:
                print("No se encontró correo para el encargado destino (llaves)")

        habitacion_dict = habitacion.to_dict() if hasattr(habitacion, 'to_dict') else {
            'id': habitacion.id,
            'room_id': habitacion.room_id,
            'user_id': habitacion.user_id,
            'control_tv': habitacion.control_tv,
            'telefono': habitacion.telefono,
            'roku': habitacion.roku,
            'toallas': habitacion.toallas,
            'botella_vidrio': habitacion.botella_vidrio,
            'notes': habitacion.notes,
        }
        if 'updated_at' not in habitacion_dict:
            updated_at = getattr(habitacion, 'updated_at', None)
            habitacion_dict['updated_at'] = updated_at.isoformat() if updated_at else None

        return jsonify({'message': 'Habitación actualizada exitosamente', 'habitacion': habitacion_dict}), 200



    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar la habitación: {str(e)}'}), 500

@habitacionesInspecciones_bp.route('/obtener_habitaciones_inspeccion', methods=['OPTIONS','GET'])
def obtener_habitaciones_inspeccion():

    if request.method == 'OPTIONS':
        return '', 200

    habitaciones = HabitacionesInspecciones.query.all()
    if not habitaciones:
        return jsonify({'error': 'No hay habitaciones disponibles'}), 404

    habitaciones_list = []
    for habitacion in habitaciones:
        habitaciones_list.append({
            'id': habitacion.id,
            'room_id': habitacion.room_id,
            'user_id': habitacion.user_id,
            'control_tv': habitacion.control_tv,
            'telefono': habitacion.telefono,
            'roku': habitacion.roku,
            'toallas': habitacion.toallas,
            'botella_vidrio': habitacion.botella_vidrio,
            'notes': habitacion.notes,
            'created_at': (habitacion.created_at.isoformat() if habitacion.created_at else None),
            'updated_at': (habitacion.updated_at.isoformat() if getattr(habitacion, 'updated_at', None) else None),
        })

    return jsonify(habitaciones_list), 200

    