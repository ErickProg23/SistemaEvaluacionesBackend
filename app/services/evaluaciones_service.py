# services/evaluaciones_service.py

from datetime import date
from app import db
from app.models import EmpleadoEncargado, Evaluacion, EvaluacionAtrasada

def detectar_evaluaciones_atrasadas():
    hoy = date.today()

    if hoy.month == 1:
        periodo_mes = 12
        periodo_anio = hoy.year - 1
    else:
        periodo_mes = hoy.month - 1
        periodo_anio = hoy.year

    encargados_con_empleados = {
        e[0] for e in db.session.query(EmpleadoEncargado.encargado_id).distinct().all()
    }

    encargados_que_evaluaron = {
        e[0] for e in db.session.query(Evaluacion.encargado_id)
        .filter_by(periodo_anio=periodo_anio, periodo_mes=periodo_mes)
        .distinct().all()
    }

    atrasados = encargados_con_empleados - encargados_que_evaluaron

    nuevos_atrasos = []

    for id_encargado in atrasados:
        existe = EvaluacionAtrasada.query.filter_by(
            id_encargado=id_encargado,
            periodo_anio=periodo_anio,
            periodo_mes=periodo_mes
        ).first()

        if not existe:
            atraso = EvaluacionAtrasada(
                id_encargado=id_encargado,
                num_semana=0,  # valor por defecto ya que ahora trabajamos por mes
                periodo_anio=periodo_anio,
                periodo_mes=periodo_mes,
                fecha_detectado=hoy
            )
            db.session.add(atraso)
            nuevos_atrasos.append(id_encargado)

    db.session.commit()

    return nuevos_atrasos, periodo_anio, periodo_mes

