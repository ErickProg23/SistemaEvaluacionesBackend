# services/evaluaciones_service.py

from datetime import date
from app import db
from app.models import EmpleadoEncargado, Encargado, Evaluacion, EvaluacionAtrasada

def detectar_evaluaciones_atrasadas():
    hoy = date.today()

    # Permitir prueba/override por variable de entorno: YYYY-MM-DD
    import os
    from datetime import datetime as dt
    override = os.getenv('EVALS_LAST_FRIDAY_OVERRIDE')
    if override:
        try:
            lf = dt.strptime(override, '%Y-%m-%d').date()
            periodo_mes = lf.month
            periodo_anio = lf.year
            last_friday = lf
        except Exception:
            override = None

    if not override:
        from calendar import monthcalendar, FRIDAY
        cal = monthcalendar(hoy.year, hoy.month)
        for week in reversed(cal):
            if week[FRIDAY] != 0:
                lf_day = week[FRIDAY]
                break
        lf_actual = date(hoy.year, hoy.month, lf_day)

        if hoy > lf_actual:
            periodo_mes = lf_actual.month
            periodo_anio = lf_actual.year
            last_friday = lf_actual
        else:
            if hoy.month == 1:
                periodo_mes = 12
                periodo_anio = hoy.year - 1
            else:
                periodo_mes = hoy.month - 1
                periodo_anio = hoy.year
            cal_prev = monthcalendar(periodo_anio, periodo_mes)
            for week in reversed(cal_prev):
                if week[FRIDAY] != 0:
                    lf_day_prev = week[FRIDAY]
                    break
            last_friday = date(periodo_anio, periodo_mes, lf_day_prev)

    encargados_con_empleados = {
        e[0]
        for e in (
            db.session.query(Encargado.id)
            .join(EmpleadoEncargado, EmpleadoEncargado.encargado_id == Encargado.id)
            .filter(Encargado.activo == True)
            .distinct()
            .all()
        )
    }

    encargados_que_evaluaron = {
        e[0] for e in db.session.query(Evaluacion.encargado_id)
        .filter(
            Evaluacion.periodo_anio == periodo_anio,
            Evaluacion.periodo_mes == periodo_mes,
            Evaluacion.fecha_evaluacion == last_friday
        )
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
                num_semana=0,
                periodo_anio=periodo_anio,
                periodo_mes=periodo_mes,
                fecha_detectado=hoy,
                activo=False,
                finalizada=False
            )
            db.session.add(atraso)
            nuevos_atrasos.append(id_encargado)

    db.session.commit()

    return nuevos_atrasos, periodo_anio, periodo_mes

