from flask import Blueprint, make_response, request, jsonify
import pytz
from sqlalchemy import Integer, case, cast, extract, func
from app.models import Empleado, Encargado, Usuario, Evaluacion, Evaluacion_Encargado, Pregunta, EvaluacionTemporal
from app import db
from collections import defaultdict
from datetime import datetime, date, timedelta
from sqlalchemy.exc import IntegrityError
import logging
import sys
# Importar los modelos necesarios

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Definición del Blueprint para las rutas de obtención de datos
evaluacion_bp = Blueprint('evaluacion_bp', __name__)


# GUARDAR EVALUACION  -------------------------------------------------------------------------------------------------------
@evaluacion_bp.route('/evaluacion/nueva', methods=['OPTIONS', 'POST'])
def guardar_evaluacion():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    try:
        data = request.json
        payload = data.get('payload')
        id_encargado = data.get('idEncargado')
        num_semana = data.get('num_semana')
        tipo_evaluacion = data.get('tipo_evaluacion')

        if not payload or not id_encargado:
            return jsonify({'error': 'Datos incompletos'}), 400

        for evaluacion_data in payload:
            empleado_id = evaluacion_data.get('empleado_id')
            calificaciones = evaluacion_data.get('calificaciones')
            comentarios = evaluacion_data.get('comentarios')
            ausente = evaluacion_data.get('ausente', False)

            if isinstance(comentarios, list):
                comentarios = ', '.join(comentarios)

            ausente_db = 1 if ausente else 0

            for aspecto_texto, calificacion in calificaciones.items():
                # Buscar el aspecto en la base de datos por nombre
                aspecto_db = Pregunta.query.filter_by(texto=aspecto_texto).first()

                if aspecto_db:
                    peso = aspecto_db.peso

                porcentaje = calificacion * peso

                nueva_evaluacion = Evaluacion(
                    empleado_id=empleado_id,
                    encargado_id=id_encargado,
                    fecha_evaluacion=datetime.now(),
                    aspecto=aspecto_texto,
                    total_puntos=calificacion,
                    porcentaje_total=porcentaje,
                    comentarios=comentarios,
                    ausente=ausente_db,
                    num_semana=num_semana,
                    tipo_evaluacion=tipo_evaluacion
                )
                db.session.add(nueva_evaluacion)

        db.session.commit()
        return jsonify({'message': 'Evaluaciones guardadas correctamente'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@evaluacion_bp.route('/evaluacion_encargado/nueva', methods=['OPTIONS', 'POST'])
def guardar_evaluacionEncargado():
    if request.method == 'OPTIONS':
        return jsonify({'message': 'OK'}), 200

    try:
        data = request.json
        payload = data.get('payload')
        id_usuario = data.get('idUsuario')
        num_semana = data.get('num_semana')
        tipo_evaluacion = data.get('tipo_evaluacion')

        if not payload or not id_usuario:
            return jsonify({'error': 'Datos incompletos'}), 400

        for evaluacion_data in payload:
            encargado_id = evaluacion_data.get('empleado_id')
            calificaciones = evaluacion_data.get('calificaciones')
            comentarios = evaluacion_data.get('comentarios')
            ausente = evaluacion_data.get('ausente', False)

            if isinstance(comentarios, list):
                comentarios = ', '.join(comentarios)

            ausente_db = 1 if ausente else 0

            for aspecto_texto, calificacion in calificaciones.items():
                # Buscar el aspecto en la base de datos por nombre
                aspecto_db = Pregunta.query.filter_by(texto=aspecto_texto).first()

                if aspecto_db:
                    peso = aspecto_db.peso

                porcentaje = calificacion * peso

                nueva_evaluacion = Evaluacion_Encargado(
                    encargado_id=encargado_id,
                    usuario_id=id_usuario,
                    fecha_evaluacion=datetime.now(),
                    aspecto=aspecto_texto,
                    total_puntos=calificacion,
                    porcentaje_total=porcentaje,
                    comentarios=comentarios,
                    ausente=ausente_db,
                    num_semana=num_semana,
                    tipo_evaluacion=tipo_evaluacion
                )
                db.session.add(nueva_evaluacion)

        db.session.commit()
        return jsonify({'message': 'Evaluaciones guardadas correctamente'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# --------------- OBTENCION DE EVALUACIONES ----------------------------------------------------------
@evaluacion_bp.route('/evaluaciones/todas', methods=['OPTIONS', 'GET'])
def obtener_evaluaciones_todas():
    try:
        from collections import defaultdict

        # Obtener todas las evaluaciones válidas (no ausentes)
        evaluaciones = Evaluacion.query.filter(Evaluacion.ausente == 0).all()

        if not evaluaciones:
            return jsonify({'error': 'No hay evaluaciones'}), 404

        # IDs únicos de empleados evaluados
        empleado_ids = {eval.empleado_id for eval in evaluaciones}

        # Obtener datos de empleados
        empleados = db.session.query(
            Empleado.id, Empleado.nombre, Empleado.tipo_evaluacion
        ).filter(Empleado.id.in_(empleado_ids)).all()

        empleados_dict = {
            emp.id: {
                'nombre': emp.nombre,
                'tipo_evaluacion': emp.tipo_evaluacion
            } for emp in empleados
        }

        aspectos_por_tipo = {
            1: 9,  # operativo
            2: 8   # administrativo
        }

        # Agrupar evaluaciones
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            evaluaciones_agrupadas[eval.empleado_id][eval.encargado_id][fecha_str].append(eval)

        resultados = defaultdict(lambda: {
            'suma_porcentaje_total': 0.0,
            'total_evaluaciones_completas': 0,
            'nombre': 'Nombre no encontrado',
            'tipo_evaluacion': 1
        })

        for empleado_id, encargados in evaluaciones_agrupadas.items():
            empleado_info = empleados_dict.get(empleado_id, {})
            tipo = empleado_info.get('tipo_evaluacion', 1)

            for encargado_id, fechas in encargados.items():
                for fecha, evals in fechas.items():
                    if tipo == 3:
                        # Agrupar por tipo_evaluacion
                        evals_por_tipo = defaultdict(list)
                        for e in evals:
                            evals_por_tipo[e.tipo_evaluacion].append(e)

                        suma_acumulada = 0.0
                        conteo_validos = 0

                        if len(evals_por_tipo[1]) == 9:
                            suma1 = sum(float(e.porcentaje_total) for e in evals_por_tipo[1])
                            suma_acumulada += suma1
                            conteo_validos += 1

                        if len(evals_por_tipo[2]) == 8:
                            suma2 = sum(float(e.porcentaje_total) for e in evals_por_tipo[2])
                            suma_acumulada += suma2
                            conteo_validos += 1

                        if conteo_validos > 0:
                            promedio_suma = suma_acumulada / conteo_validos
                            resultados[empleado_id]['total_evaluaciones_completas'] += 1
                            resultados[empleado_id]['suma_porcentaje_total'] += promedio_suma
                            resultados[empleado_id]['nombre'] = empleado_info.get('nombre', 'Nombre no encontrado')
                            resultados[empleado_id]['tipo_evaluacion'] = tipo

                    else:
                        aspectos_esperados = aspectos_por_tipo.get(tipo, 9)
                        if len(evals) == aspectos_esperados:
                            suma = sum(float(e.porcentaje_total) for e in evals)
                            resultados[empleado_id]['total_evaluaciones_completas'] += 1
                            resultados[empleado_id]['suma_porcentaje_total'] += suma
                            resultados[empleado_id]['nombre'] = empleado_info.get('nombre', 'Nombre no encontrado')
                            resultados[empleado_id]['tipo_evaluacion'] = tipo

        # Calcular porcentaje final (base fija de 500 por evaluación)
        for empleado_id, datos in resultados.items():
            total = datos['total_evaluaciones_completas']
            if total > 0:
                porcentaje_final = (datos['suma_porcentaje_total'] / (500 * total)) * 100
                datos['porcentaje_final'] = min(porcentaje_final, 100.0)
            else:
                datos['porcentaje_final'] = 0.0

        # Calcular promedio general
        promedios = [datos['porcentaje_final'] for datos in resultados.values() if datos['total_evaluaciones_completas'] > 0]
        promedio_general = sum(promedios) / len(promedios) if promedios else 0

        return jsonify({
            'promedio_general': round(promedio_general, 2),
            'total_empleados': len(promedios),
            'detalle_empleados': [
                {
                    'nombre': datos['nombre'],
                    'empleado_id': emp_id,
                    'calificacion_final': round(datos['porcentaje_final'], 2),
                    'total_evaluaciones': datos['total_evaluaciones_completas']
                } for emp_id, datos in resultados.items() if datos['total_evaluaciones_completas'] > 0
            ]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --------------- OBTENCION DE EVALUACIONES CON ENCARGADOS ----------------------------------------------------------
@evaluacion_bp.route('/evaluaciones/completas-por-encargado', methods=['GET', 'OPTIONS'])
def obtener_evaluaciones_completas_por_encargado():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Parámetros
        encargado_id = request.args.get('encargado_id', type=int)
        periodo_tipo = request.args.get('periodo_tipo', 'month')
        periodo_valor = request.args.get('periodo_valor')

        if not encargado_id:
            return jsonify({'error': 'encargado_id es requerido'}), 400
        
        # Obtener tipo de evaluación del encargado
        encargado = Encargado.query.get(encargado_id)
        if not encargado:
            return jsonify({'error': 'Encargado no encontrado'}), 404

        tipo_evaluacion_encargado = encargado.tipo_evaluacion
        aspectos_necesarios = 9 if tipo_evaluacion_encargado == 1 else 8 if tipo_evaluacion_encargado == 2 else 0


        # Filtro base
        base_query = Evaluacion.query.filter(
            Evaluacion.encargado_id == encargado_id,
        )

        # Filtro de periodo
        if periodo_tipo and periodo_valor:
            if periodo_tipo == 'week':
                num_semana = int(periodo_valor)
                base_query = base_query.filter(Evaluacion.num_semana == num_semana)

            elif periodo_tipo == 'month':
                from datetime import datetime, date, timedelta

                if '-' in periodo_valor:
                    year, month = map(int, periodo_valor.split('-'))
                else:
                    year = datetime.now().year
                    month = int(periodo_valor)

                fecha_inicio = date(year, month, 1)
                fecha_fin = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)

                base_query = base_query.filter(
                    Evaluacion.fecha_evaluacion >= fecha_inicio,
                    Evaluacion.fecha_evaluacion <= fecha_fin
                )
            elif periodo_tipo == 'year':
                year = int(periodo_valor)
                fecha_inicio = date(year, 1, 1)
                fecha_fin = date(year, 12, 31)

                base_query = base_query.filter(
                    Evaluacion.fecha_evaluacion >= fecha_inicio,
                    Evaluacion.fecha_evaluacion <= fecha_fin
                )
            else:
                return jsonify({'error': 'periodo_tipo inválido'}), 400

        evaluaciones = base_query.all()
        if not evaluaciones:
            return jsonify({'evaluaciones_completas': []}), 200

        from collections import defaultdict

        # Agrupar evaluaciones por empleado
        evaluaciones_por_empleado = defaultdict(list)
        for eval in evaluaciones:
            evaluaciones_por_empleado[eval.empleado_id].append(eval)

        # Obtener empleados
        empleado_ids = list(evaluaciones_por_empleado.keys())
        empleados = Empleado.query.filter(Empleado.id.in_(empleado_ids)).all()
        empleados_dict = {e.id: e for e in empleados}

        resultados = []

        for empleado_id, evals in evaluaciones_por_empleado.items():
            empleado = empleados_dict.get(empleado_id)
            if not empleado:
                continue

            # Agrupar por fecha
            evaluaciones_por_fecha = defaultdict(list)
            for eval in evals:
                fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
                evaluaciones_por_fecha[fecha_str].append(eval)

            calificaciones_individuales = []

            for fecha, registros in evaluaciones_por_fecha.items():
                if len(registros) == aspectos_necesarios:
                    suma = sum(float(r.porcentaje_total) for r in registros)
                    calificacion = (suma / 500) * 100
                    calificacion = min(calificacion, 100)
                    calificaciones_individuales.append(calificacion)

            if calificaciones_individuales:
                promedio = sum(calificaciones_individuales) / len(calificaciones_individuales)
                ultima_fecha = max(e.fecha_evaluacion for e in evals)

                resultados.append({
                    'empleado_id': empleado_id,
                    'nombre_empleado': empleado.nombre,
                    'calificacion_promedio': round(promedio, 2),
                    'ultima_fecha': ultima_fecha.strftime('%Y-%m-%d'),
                    'encargado_id': encargado_id
                })

        return jsonify({'evaluaciones_completas': resultados}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@evaluacion_bp.route('/evaluaciones', methods=['OPTIONS','GET'])
def obtener_evaluaciones():
    #Validar parametros
    encargado_id = request.args.get('encargado_id')
    if not encargado_id:
        return jsonify({'error': 'Se requiere ID de encargado'}), 400

    try:
        # 1. Obtener la fecha de la evaluación más reciente para cada empleado
        subquery = db.session.query(
            Evaluacion.empleado_id,
            db.func.max(Evaluacion.fecha_evaluacion).label('fecha_reciente')
        ).filter(
            Evaluacion.encargado_id == encargado_id
        ).group_by(
            Evaluacion.empleado_id
        ).subquery()

        # 2. Obtener TODAS las evaluaciones más recientes para cada empleado
        evaluaciones = db.session.query(Evaluacion).join(
            subquery,
            db.and_(
                Evaluacion.empleado_id == subquery.c.empleado_id,
                Evaluacion.fecha_evaluacion == subquery.c.fecha_reciente,
                Evaluacion.encargado_id == encargado_id
            )
        ).all()

        if not evaluaciones:
            return jsonify({'error': 'No hay evaluaciones'}), 404

        # Obtener IDs de empleados únicos
        empleado_ids = {eval.empleado_id for eval in evaluaciones}

        # 3. Consultar nombres de empleados
        empleados = db.session.query(Empleado.id, Empleado.nombre).filter(
            Empleado.id.in_(empleado_ids)
        ).all()
        empleados_dict = {emp.id: emp.nombre for emp in empleados}

        # 4. Agrupar evaluaciones por empleado y fecha
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            empleado_id = eval.empleado_id
            evaluaciones_agrupadas[empleado_id][fecha_str].append(eval)
        
        # 5. Procesar datos por empleado
        resultados = defaultdict(lambda: {
            'suma_porcentaje_total': 0.0,
            'total_evaluaciones_completas': 0,
            'nombre': 'Nombre no encontrado',
            'tiene_ausencia': False,
            'fecha_evaluacion': None
        })
        
        # Inicializar datos para todos los empleados
        for empleado_id in empleado_ids:
            resultados[empleado_id]['nombre'] = empleados_dict.get(empleado_id, 'Nombre no encontrado')
        
        # Contar evaluaciones completas (con 9 aspectos) y sumar porcentajes
        for empleado_id, fechas in evaluaciones_agrupadas.items():
            for fecha, evals in fechas.items():
                # Guardar la fecha de evaluación
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                if resultados[empleado_id]['fecha_evaluacion'] is None or fecha_dt > resultados[empleado_id]['fecha_evaluacion']:
                    resultados[empleado_id]['fecha_evaluacion'] = fecha_dt
                
                # Verificar si hay alguna evaluación con ausente=1 para este empleado y fecha
                if any(eval.ausente == 1 for eval in evals):
                    resultados[empleado_id]['tiene_ausencia'] = True
                
                # Solo considerar evaluaciones completas donde ausente=0
                evals_presentes = [eval for eval in evals if eval.ausente == 0]
                
                # Si hay 9 aspectos con ausente=0, consideramos que es una evaluación completa
                if evals_presentes:
                    tipo_eval = evals_presentes[0].tipo_evaluacion
                    total_aspectos_requeridos = 9 if tipo_eval == 1 else 8


                    if len(evals_presentes) == total_aspectos_requeridos:
                        resultados[empleado_id]['total_evaluaciones_completas'] += 1
                        # Sumar los porcentajes de todos los aspectos para esta evaluación
                        suma_porcentaje = sum(float(eval.porcentaje_total) for eval in evals_presentes)
                        resultados[empleado_id]['suma_porcentaje_total'] += suma_porcentaje

        # 6. Calcular porcentaje_final correctamente
        for empleado_id, datos in resultados.items():
            if datos['total_evaluaciones_completas'] > 0:
                # Calcular el promedio de porcentaje final
                # Cada evaluación completa suma 500 puntos (9 aspectos)
                datos['porcentaje_final'] = (datos['suma_porcentaje_total'] / (500 * datos['total_evaluaciones_completas'])) * 100
                datos['porcentaje_final'] = min(datos['porcentaje_final'], 100.0)  # Limitar a 100%
            else:
                datos['porcentaje_final'] = 0.0

        # 7. Calcular promedios solo de empleados con evaluaciones completas y sin ausencias
        promedios = [datos['porcentaje_final'] for empleado_id, datos in resultados.items() 
                    if datos['total_evaluaciones_completas'] > 0]
        promedio_general = sum(promedios) / len(promedios) if promedios else 0

        # 8. Determinar el rango de fechas para el período
        fechas_evaluacion = [datos['fecha_evaluacion'] for datos in resultados.values() if datos['fecha_evaluacion'] is not None]
        if fechas_evaluacion:
            fecha_min = min(fechas_evaluacion)
            fecha_max = max(fechas_evaluacion)
        else:
            # Si no hay fechas, usar la fecha actual
            fecha_min = fecha_max = datetime.now()

        # 9. Formatear respuesta
        return jsonify({
            'promedio_general': round(promedio_general, 2),
            'total_empleados': len(resultados),
            'periodo':{
                'inicio': fecha_min,
                'fin': fecha_max
            },
            'detalle_empleados':[
                {
                    'nombre': datos['nombre'],
                    'empleado_id': emp_id,
                    'calificacion_final': round(datos['porcentaje_final'], 2) if 'porcentaje_final' in datos else 0,
                    'total_evaluaciones': datos['total_evaluaciones_completas'],
                    'tiene_ausencia': datos['tiene_ausencia'],
                    'fecha_evaluacion': datos['fecha_evaluacion'].strftime('%Y-%m-%d') if datos['fecha_evaluacion'] else None
                } for emp_id, datos in resultados.items()
            ]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}),500

@evaluacion_bp.route('/evaluaciones-usuario', methods=['OPTIONS','GET'])
def obtener_evaluacionesUsuario():
    #Validar parametros
    usuario_id = request.args.get('usuario_id')
    if not usuario_id:
        return jsonify({'error': 'Se requiere ID del usuario'}), 400

    try:
        # 1. Obtener la fecha de la evaluación más reciente para cada empleado
        subquery = db.session.query(
            Evaluacion_Encargado.encargado_id,
            db.func.max(Evaluacion_Encargado.fecha_evaluacion).label('fecha_reciente')
        ).filter(
            Evaluacion_Encargado.usuario_id == usuario_id
        ).group_by(
            Evaluacion_Encargado.encargado_id
        ).subquery()

        # 2. Obtener TODAS las evaluaciones más recientes para cada empleado
        evaluaciones = db.session.query(Evaluacion_Encargado).join(
            subquery,
            db.and_(
                Evaluacion_Encargado.encargado_id == subquery.c.encargado_id,
                Evaluacion_Encargado.fecha_evaluacion == subquery.c.fecha_reciente,
                Evaluacion_Encargado.usuario_id == usuario_id
            )
        ).all()

        if not evaluaciones:
            return jsonify({'error': 'No hay evaluaciones'}), 404

        # Obtener IDs de empleados únicos
        encargado_ids = {eval.encargado_id for eval in evaluaciones}

        # 3. Consultar nombres de empleados y tipo_evaluacion desde la tabla Encargado
        encargados = db.session.query(Encargado.id, Encargado.nombre, Encargado.tipo_evaluacion).filter(
            Encargado.id.in_(encargado_ids)
        ).all()
        encargado_dict = {enc.id: {'nombre': enc.nombre, 'tipo_evaluacion': enc.tipo_evaluacion} for enc in encargados}

        # 4. Agrupar evaluaciones por encargado y fecha
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            encargado_id = eval.encargado_id
            evaluaciones_agrupadas[encargado_id][fecha_str].append(eval)
        
        # 5. Procesar datos por encargado
        resultados = defaultdict(lambda: {
            'suma_porcentaje_total': 0.0,
            'total_evaluaciones_completas': 0,
            'nombre': 'Nombre no encontrado',
            'tiene_ausencia': False,
            'fecha_evaluacion': None
        })
        
        # Inicializar datos para todos los encargados
        for encargado_id in encargado_ids:
            resultados[encargado_id]['nombre'] = encargado_dict.get(encargado_id, {}).get('nombre', 'Nombre no encontrado')
        
        # Contar evaluaciones completas (con 9 o 8 aspectos según tipo_evaluacion del encargado) y sumar porcentajes
        for encargado_id, fechas in evaluaciones_agrupadas.items():
            tipo_encargado = encargado_dict.get(encargado_id, {}).get('tipo_evaluacion', 1)
            for fecha, evals in fechas.items():
                # Guardar la fecha de evaluación
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                if resultados[encargado_id]['fecha_evaluacion'] is None or fecha_dt > resultados[encargado_id]['fecha_evaluacion']:
                    resultados[encargado_id]['fecha_evaluacion'] = fecha_dt
                
                # Verificar si hay alguna evaluación con ausente=1 para este encargado y fecha
                if any(eval.ausente == 1 for eval in evals):
                    resultados[encargado_id]['tiene_ausencia'] = True
                
                # Solo considerar evaluaciones completas donde ausente=0
                evals_presentes = [eval for eval in evals if eval.ausente == 0]
                
                if evals_presentes:
                    total_aspectos_requeridos = 9 if tipo_encargado == 1 else 8

                    if len(evals_presentes) == total_aspectos_requeridos:
                        resultados[encargado_id]['total_evaluaciones_completas'] += 1
                        # Sumar los porcentajes de todos los aspectos para esta evaluación
                        suma_porcentaje = sum(float(eval.porcentaje_total) for eval in evals_presentes)
                        resultados[encargado_id]['suma_porcentaje_total'] += suma_porcentaje

        # 6. Calcular porcentaje_final correctamente
        for encargado_id, datos in resultados.items():
            if datos['total_evaluaciones_completas'] > 0:
                # Calcular el promedio de porcentaje final
                # Cada evaluación completa suma 500 puntos (9 aspectos)
                datos['porcentaje_final'] = (datos['suma_porcentaje_total'] / (500 * datos['total_evaluaciones_completas'])) * 100
                datos['porcentaje_final'] = min(datos['porcentaje_final'], 100.0)  # Limitar a 100%
            else:
                datos['porcentaje_final'] = 0.0

        # 7. Calcular promedios solo de encargados con evaluaciones completas y sin ausencias
        promedios = [datos['porcentaje_final'] for encargado_id, datos in resultados.items() 
                    if datos['total_evaluaciones_completas'] > 0]
        promedio_general = sum(promedios) / len(promedios) if promedios else 0

        # 8. Determinar el rango de fechas para el período
        fechas_evaluacion = [datos['fecha_evaluacion'] for datos in resultados.values() if datos['fecha_evaluacion'] is not None]
        if fechas_evaluacion:
            fecha_min = min(fechas_evaluacion)
            fecha_max = max(fechas_evaluacion)
        else:
            # Si no hay fechas, usar la fecha actual
            fecha_min = fecha_max = datetime.now()

        # 9. Formatear respuesta
        return jsonify({
            'promedio_general': round(promedio_general, 2),
            'total_empleados': len(resultados),
            'detalle_empleados': [
                {
                    'nombre': datos['nombre'],
                    'encargado': enc_id,
                    'calificacion_final': round(datos['porcentaje_final'], 2) if 'porcentaje_final' in datos else 0,
                    'total_evaluaciones': datos['total_evaluaciones_completas'],
                    'tiene_ausencia': datos['tiene_ausencia'],
                    'fecha_evaluacion': datos['fecha_evaluacion'].strftime('%Y-%m-%d') if datos['fecha_evaluacion'] else None
                } for enc_id, datos in resultados.items()
            ]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}),500


# --------------- OBTENER EVALUACIONES COMPLETADAS POR ENCARGADO ----------------------------------------------------------
@evaluacion_bp.route('/evaluaciones/completasDestiempoUltimoMes', methods=['OPTIONS', 'GET'])
def obtener_evaluaciones_completas_destiempo_ultimo_mes():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        hoy = datetime.today()
        hace_un_mes = hoy - timedelta(days=30)

        # 1. Obtener el número de empleados por encargado
        subquery_empleados = db.session.query(
            Evaluacion.encargado_id,
            Evaluacion.empleado_id
        ).distinct().subquery()

        empleados_por_encargado = {}
        empleados = db.session.query(
            subquery_empleados.c.encargado_id,
            func.count(subquery_empleados.c.empleado_id)
        ).group_by(subquery_empleados.c.encargado_id).all()

        for encargado_id, total_empleados in empleados:
            empleados_por_encargado[encargado_id] = total_empleados

        # 2. Evaluaciones fuera de tiempo en el último mes
        query = db.session.query(
            Evaluacion.encargado_id,
            Evaluacion.empleado_id,
            func.date(Evaluacion.fecha_evaluacion).label('fecha'),
            Evaluacion.tipo_evaluacion,
            func.count(Evaluacion.id).label('aspectos_count')
        ).filter(
            Evaluacion.a_tiempo == 0,
            Evaluacion.fecha_evaluacion >= hace_un_mes
        ).group_by(
            Evaluacion.encargado_id,
            Evaluacion.empleado_id,
            func.date(Evaluacion.fecha_evaluacion),
            Evaluacion.tipo_evaluacion
        ).all()

        # 3. Agrupar por encargado + fecha
        evaluaciones_temporales = {}

        for encargado_id, empleado_id, fecha, tipo, aspectos in query:
            requisitos = 9 if tipo == 1 else 8
            if aspectos == requisitos:
                key = (encargado_id, fecha)
                if key not in evaluaciones_temporales:
                    evaluaciones_temporales[key] = set()
                evaluaciones_temporales[key].add(empleado_id)

        # 4. Validar que se evaluó a todos los empleados de ese encargado
        evaluaciones_destiempo_completas = {}
        for (encargado_id, fecha), empleados_evaluados in evaluaciones_temporales.items():
            total_esperado = empleados_por_encargado.get(encargado_id, 0)
            if len(empleados_evaluados) == total_esperado:
                if encargado_id not in evaluaciones_destiempo_completas:
                    evaluaciones_destiempo_completas[encargado_id] = 0
                evaluaciones_destiempo_completas[encargado_id] += 1

        if not evaluaciones_destiempo_completas:
            return jsonify({'message': 'No hay evaluaciones completas fuera de tiempo en el último mes'}), 404

        # Obtener nombres de los encargados
        encargado_ids = list(evaluaciones_destiempo_completas.keys())
        encargados = Encargado.query.filter(Encargado.id.in_(encargado_ids)).all()
        encargados_dict = {enc.id: enc.nombre for enc in encargados}

        resultados = [
            {
                'encargado_id': encargado_id,
                'nombre': encargados_dict.get(encargado_id, 'Nombre no encontrado'),
                'evaluaciones_destiempo_completas': total
            }
            for encargado_id, total in evaluaciones_destiempo_completas.items()
        ]

        return jsonify({'resultados': resultados}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --------------- OBTENER EVALUACIONES FILTRADAS ----------------------------------------------------------
@evaluacion_bp.route('/evaluaciones/filtradas', methods=['OPTIONS', 'GET'])
def obtener_evaluaciones_filtradas():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Obtener parámetros de filtrado
        encargado_id = request.args.get('encargado_id')
        empleado_id = request.args.get('empleado_id')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        periodo_tipo = request.args.get('periodo_tipo')  # Nuevo parámetro: tipo de periodo (año, mes, semana)
        periodo_valor = request.args.get('periodo_valor')  # Nuevo parámetro: valor del periodo
        debug = request.args.get('debug') == '1'  # Parámetro de depuración
        
        
        # Información de depuración
        debug_info = {
            'parametros': {
                'encargado_id': encargado_id,
                'empleado_id': empleado_id,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'periodo_tipo': periodo_tipo,
                'periodo_valor': periodo_valor
            },
            'conteos': {}
        }
        
        # Construir la consulta base
        query = Evaluacion.query
        
        # Contar registros iniciales
        total_inicial = query.count()
        debug_info['conteos']['total_inicial'] = total_inicial
        
        # Aplicar filtros si se proporcionan
        if encargado_id:
            query = query.filter(Evaluacion.encargado_id == encargado_id)
            debug_info['conteos']['despues_filtro_encargado'] = query.count()
        
        if empleado_id:
            query = query.filter(Evaluacion.empleado_id == empleado_id)
            debug_info['conteos']['despues_filtro_empleado'] = query.count()
        
        # Filtrar por periodo si se proporciona
        if periodo_tipo and periodo_valor:
            try:
                # Mapear periodo a español
                periodo_mapeado = {
                    'month': 'mes',
                    'year': 'año',
                    'week': 'semana',
                    'mes': 'mes',  # Compatibilidad con español
                    'año': 'año',
                    'semana': 'semana'
                }.get(periodo_tipo, None)
                
                if not periodo_mapeado:
                    raise ValueError('Periodo no válido. Use "month", "year" o "week".')
                
                current_year = datetime.now().year
                
                # Generar fecha_seleccionada según el periodo
                if periodo_mapeado == 'mes':
                    # Si el valor es solo el mes (ej: "05" o "4")
                    if periodo_valor.isdigit() and '-' not in periodo_valor:
                        year = current_year
                        month = int(periodo_valor)
                        fecha_seleccionada = date(year, month, 1)
                    else:
                        # Si en algún caso envía "YYYY-MM"
                        try:
                            year, month = map(int, periodo_valor.split('-'))
                            fecha_seleccionada = date(year, month, 1)
                        except ValueError:
                            raise ValueError(f"Formato de mes inválido: {periodo_valor}. Use MM o YYYY-MM")
                elif periodo_mapeado == 'año':
                    # El valor es el año (ej: "2023")
                    year = int(periodo_valor)
                    fecha_seleccionada = date(year, 1, 1)  # 1 de enero
                elif periodo_mapeado == 'semana':
                    try:
                        if '-' not in periodo_valor:
                            # Caso 1: Solo el número de semana (ej: "15")
                            year = current_year  # Año actual
                            week = int(periodo_valor)
                        else:
                            # Caso 2: Formato YYYY-Www (ej: "2024-W15")
                            # Verificar que el formato sea correcto
                            if not periodo_valor.startswith('W') and 'W' in periodo_valor:
                                parts = periodo_valor.split('-W')
                                if len(parts) != 2:
                                    raise ValueError("Formato inválido para semana. Use YYYY-Www (ej: 2024-W15)")
                                year = int(parts[0])
                                week = int(parts[1])
                            else:
                                raise ValueError("Formato inválido para semana. Use YYYY-Www o solo el número de semana")
                        
                        # Validar rango de la semana
                        if week < 1 or week > 53:
                            raise ValueError("Semana debe estar entre 1 y 53")
                        
                        # Para filtrado por semana, usamos directamente el campo num_semana
                        query = query.filter(Evaluacion.num_semana == week)
                        
                        # Si también se especificó el año, filtramos por año
                        if '-' in periodo_valor:
                            # Extraer el año de la fecha_evaluacion
                            query = query.filter(extract('year', Evaluacion.fecha_evaluacion) == year)
                        
                        debug_info['conteos']['despues_filtro_semana'] = query.count()
                        
                        # No necesitamos calcular fecha_inicio y fecha_fin para semana
                        # ya que filtramos directamente por num_semana
                    except ValueError as e:
                        raise ValueError(f'Error en semana: {str(e)}')
                
                # Calcular rango de fechas para mes y año
                if periodo_mapeado in ['mes', 'año']:
                    fecha_inicio_obj, fecha_fin_obj = calcular_rango_fechas(periodo_mapeado, fecha_seleccionada)
                    
                    if not fecha_inicio_obj or not fecha_fin_obj:
                        raise ValueError('Formato de fecha inválido para el periodo seleccionado')
                    
                    query = query.filter(
                        Evaluacion.fecha_evaluacion >= fecha_inicio_obj,
                        Evaluacion.fecha_evaluacion <= fecha_fin_obj
                    )
                    
                    debug_info['conteos']['despues_filtro_periodo'] = query.count()
            
            except ValueError as e:
                debug_info['errores'] = debug_info.get('errores', []) + [f"Error en periodo: {str(e)}"]
                if debug:
                    return jsonify({'error': str(e), 'debug': debug_info}), 400
                return jsonify({'error': str(e)}), 400
        
        # Filtrar por rango de fechas si se proporcionan (y no se usó periodo)
        elif fecha_inicio or fecha_fin:
            if fecha_inicio:
                try:
                    fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                    query = query.filter(func.date(Evaluacion.fecha_evaluacion) >= fecha_inicio_obj)
                    debug_info['conteos']['despues_filtro_fecha_inicio'] = query.count()
                except ValueError as e:
                    debug_info['errores'] = debug_info.get('errores', []) + [f"Error en fecha_inicio: {str(e)}"]
            
            if fecha_fin:
                try:
                    fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                    query = query.filter(func.date(Evaluacion.fecha_evaluacion) <= fecha_fin_obj)
                    debug_info['conteos']['despues_filtro_fecha_fin'] = query.count()
                except ValueError as e:
                    debug_info['errores'] = debug_info.get('errores', []) + [f"Error en fecha_fin: {str(e)}"]
        
        # Ejecutar la consulta
        evaluaciones = query.all()
        debug_info['conteos']['total_evaluaciones'] = len(evaluaciones)
        
        if not evaluaciones:
            if debug:
                return jsonify({'resultados': [], 'debug': debug_info}), 200
            return jsonify([]), 200  # Devolver array vacío si no hay resultados
        
        # Agrupar evaluaciones por empleado y encargado
        # Modificado para agrupar solo por empleado y encargado, no por fecha
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        
        for eval in evaluaciones:
            empleado_id = eval.empleado_id
            encargado_id = eval.encargado_id
            evaluaciones_agrupadas[empleado_id][encargado_id].append(eval)
        
        # Obtener información de empleados y encargados
        empleado_ids = set(eval.empleado_id for eval in evaluaciones)
        encargado_ids = set(eval.encargado_id for eval in evaluaciones)
        
        debug_info['ids'] = {
            'empleado_ids': list(empleado_ids),
            'encargado_ids': list(encargado_ids)
        }
        
        empleados = Empleado.query.filter(Empleado.id.in_(empleado_ids)).all()
        encargados = Encargado.query.filter(Encargado.id.in_(encargado_ids)).all()
        
        debug_info['conteos']['empleados_encontrados'] = len(empleados)
        debug_info['conteos']['encargados_encontrados'] = len(encargados)
        
        empleados_dict = {emp.id: emp for emp in empleados}
        encargados_dict = {enc.id: enc for enc in encargados}
        
        # Procesar resultados
        resultados = []
        empleados_no_encontrados = []
        encargados_no_encontrados = []
        
        for emp_id, encargados_data in evaluaciones_agrupadas.items():
            empleado = empleados_dict.get(emp_id)
            
            if not empleado:
                empleados_no_encontrados.append(emp_id)
                continue  # Saltar si no se encuentra el empleado
            
            # Obtener el tipo de evaluación del empleado
            tipo_evaluacion = empleado.tipo_evaluacion
            # Determinar el número de aspectos según el tipo de evaluación
            num_aspectos_esperados = 9 if tipo_evaluacion == 1 else 8
            divisor_calificacion = 500 if tipo_evaluacion == 1 else 500
            
            for enc_id, evals_list in encargados_data.items():
                encargado = encargados_dict.get(enc_id)
                
                if not encargado:
                    encargados_no_encontrados.append(enc_id)
                    continue  # Saltar si no se encuentra el encargado
                
                # Filtrar solo las evaluaciones donde ausente=0 (empleado presente)
                evals_presentes = [eval for eval in evals_list if eval.ausente == 0]
                evals_ausentes = [eval for eval in evals_list if eval.ausente == 1]
                
                # Si todas las evaluaciones son de ausentes, crear un registro de ausente
                if not evals_presentes and evals_ausentes:
                    resultados.append({
                        'fecha': evals_ausentes[0].fecha_evaluacion.strftime('%Y-%m-%d'),
                        'empleado_id': emp_id,
                        'empleado_nombre': empleado.nombre,
                        'encargado_id': enc_id,
                        'encargado_nombre': encargado.nombre,
                        'ausente': True,
                        'comentarios': evals_ausentes[0].comentarios if evals_ausentes else '',
                        'calificacion_total': 0,
                        'aspectos': [],
                        'tipo_evaluacion': tipo_evaluacion,
                        'evaluaciones_promediadas': len(evals_ausentes)
                    })
                # Si hay evaluaciones donde el empleado estuvo presente, procesarlas
                elif evals_presentes:
                    # Agrupar evaluaciones por aspecto para calcular promedios
                    aspectos_agrupados = defaultdict(list)
                    todos_comentarios = []
                    
                    for eval in evals_presentes:  # Solo usar evaluaciones donde ausente=0
                        aspectos_agrupados[eval.aspecto].append({
                            'calificacion': float(eval.total_puntos),
                            'porcentaje': float(eval.porcentaje_total)
                        })
                        if eval.comentarios and eval.comentarios.strip():
                            todos_comentarios.append(eval.comentarios)
                    
                    # Calcular promedios por aspecto
                    aspectos_promediados = []
                    suma_porcentaje = 0
                    
                    for aspecto, valores in aspectos_agrupados.items():
                        calificacion_promedio = sum(v['calificacion'] for v in valores) / len(valores)
                        porcentaje_promedio = sum(v['porcentaje'] for v in valores) / len(valores)
                        
                        aspectos_promediados.append({
                            'aspecto': aspecto,
                            'calificacion': round(calificacion_promedio, 2),
                            'porcentaje': round(porcentaje_promedio, 2)
                        })
                        suma_porcentaje += porcentaje_promedio
                    
                    # Calcular calificación total promedio
                    # Usar el divisor correcto según el tipo de evaluación
                    calificacion_total = (suma_porcentaje / divisor_calificacion) * 100 if aspectos_promediados else 0
                    
                    # Unir todos los comentarios o usar el primero si no hay múltiples
                    comentarios_finales = ' | '.join(todos_comentarios) if len(todos_comentarios) > 1 else \
                                         todos_comentarios[0] if todos_comentarios else ''
                    
                    # Usar la fecha más reciente para el registro
                    fechas_evaluacion = [eval.fecha_evaluacion for eval in evals_presentes]
                    fecha_mas_reciente = max(fechas_evaluacion).strftime('%Y-%m-%d') if fechas_evaluacion else ''
                    
                    resultados.append({
                        'fecha': fecha_mas_reciente,
                        'empleado_id': emp_id,
                        'empleado_nombre': empleado.nombre,
                        'encargado_id': enc_id,
                        'encargado_nombre': encargado.nombre,
                        'ausente': False,
                        'comentarios': comentarios_finales,
                        'calificacion_total': round(calificacion_total, 2),
                        'aspectos': aspectos_promediados,
                        'tipo_evaluacion': tipo_evaluacion,
                        'evaluaciones_promediadas': len(evals_presentes)
                    })
        
        debug_info['errores_procesamiento'] = {
            'empleados_no_encontrados': empleados_no_encontrados,
            'encargados_no_encontrados': encargados_no_encontrados
        }
        
        debug_info['conteos']['resultados_finales'] = len(resultados)
        
        # Ordenar por fecha (más reciente primero)
        resultados.sort(key=lambda x: x['fecha'], reverse=True)
        
        if debug:
            return jsonify({'resultados': resultados, 'debug': debug_info}), 200
        return jsonify(resultados), 200
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        return jsonify({
            'error': str(e),
            'traceback': error_traceback
        }), 500

@evaluacion_bp.route('/evaluaciones/exportar-csv', methods=['OPTIONS', 'GET'])
def exportar_evaluaciones_csv():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print("\n=== PARÁMETROS RECIBIDOS PARA EXPORTACIÓN ===")
        print(f"periodo_tipo: {request.args.get('periodo_tipo')}")
        print(f"periodo_valor: {request.args.get('periodo_valor')}")
        print(f"agrupar: {request.args.get('agrupar', 'false')}")

        # Obtener parámetros
        periodo = request.args.get('periodo_tipo', 'mes')
        periodo_valor = request.args.get('periodo_valor')
        agrupar = request.args.get('agrupar', 'false').lower() == 'true'  # Nuevo parámetro para agrupar
        current_year = datetime.now().year
        
        # Validar parámetros
        if not periodo_valor:
            return jsonify({'error': 'Se requiere periodo_valor'}), 400

        # Mapear periodo a español
        periodo_mapeado = {
            'month': 'mes',
            'year': 'año',
            'week': 'semana',
            'mes': 'mes',  # Compatibilidad con español
            'año': 'año',
            'semana': 'semana'
        }.get(periodo, None)

        if not periodo_mapeado:
            return jsonify({'error': 'Periodo no válido. Use "month", "year" o "week".'}), 400

        # Generar fecha_seleccionada según el periodo
        try:
            if periodo_mapeado == 'mes':
                # Si el valor es solo el mes (ej: "05" o "4")
                if periodo_valor.isdigit() and '-' not in periodo_valor:
                    year = current_year
                    month = int(periodo_valor)
                    fecha_seleccionada = date(year, month, 1)
                else:
                    # Si en algún caso envía "YYYY-MM"
                    try:
                        year, month = map(int, periodo_valor.split('-'))
                        fecha_seleccionada = date(year, month, 1)
                    except ValueError:
                        raise ValueError(f"Formato de mes inválido: {periodo_valor}. Use MM o YYYY-MM")
            elif periodo_mapeado == 'año':
                # El valor es el año (ej: "2023")
                year = int(periodo_valor)
                fecha_seleccionada = date(year, 1, 1)  # 1 de enero
            elif periodo_mapeado == 'semana':
                try:
                    if '-' not in periodo_valor:
                        # Caso 1: Solo el número de semana (ej: "15")
                        year = current_year  # Año actual
                        week = int(periodo_valor)
                    else:
                        # Caso 2: Formato YYYY-Www (ej: "2024-W15")
                        # Verificar que el formato sea correcto
                        if not periodo_valor.startswith('W') and 'W' in periodo_valor:
                            parts = periodo_valor.split('-W')
                            if len(parts) != 2:
                                raise ValueError("Formato inválido para semana. Use YYYY-Www (ej: 2024-W15)")
                            year = int(parts[0])
                            week = int(parts[1])
                        else:
                            raise ValueError("Formato inválido para semana. Use YYYY-Www o solo el número de semana")
                    
                    # Validar rango de la semana
                    if week < 1 or week > 53:
                        raise ValueError("Semana debe estar entre 1 y 53")
                    
                    fecha_seleccionada = datetime.fromisocalendar(year, week, 1).date()
                
                except ValueError as e:
                    return jsonify({'error': f'Error en semana: {str(e)}'}), 400
        except ValueError as e:
            return jsonify({'error': f'Error: {str(e)}'}), 400

        # Validaciones adicionales
        if periodo_mapeado == 'mes' and not (1 <= fecha_seleccionada.month <= 12):
            return jsonify({'error': 'Mes inválido (debe ser 1-12)'}), 400

        if periodo_mapeado == 'semana' and not (1 <= fecha_seleccionada.isocalendar()[1] <= 53):
            return jsonify({'error': 'Semana inválida (1-53)'}), 400

        if periodo_mapeado == 'año' and not (2000 <= fecha_seleccionada.year <= 2100):
            return jsonify({'error': 'Año inválido (2000-2100)'}), 400

        # Calcular rango de fechas
        fecha_inicio, fecha_fin = calcular_rango_fechas(periodo_mapeado, fecha_seleccionada)
        
        if not fecha_inicio or not fecha_fin:
            return jsonify({'error': 'Formato de fecha inválido para el periodo seleccionado'}), 400
        
        # Construir la consulta base para obtener todas las evaluaciones en el rango
        query = Evaluacion.query.filter(
            Evaluacion.fecha_evaluacion >= fecha_inicio,
            Evaluacion.fecha_evaluacion <= fecha_fin
        ).order_by(Evaluacion.empleado_id, Evaluacion.fecha_evaluacion)
        
        # Ejecutar la consulta
        evaluaciones = query.all()
        
        if not evaluaciones:
            return jsonify({'message': 'No hay evaluaciones para los filtros seleccionados'}), 404
        
        # Obtener IDs de empleados y encargados únicos
        empleado_ids = {eval.empleado_id for eval in evaluaciones}
        encargado_ids = {eval.encargado_id for eval in evaluaciones}
        
        # Consultar nombres de empleados y sus tipos de evaluación
        empleados = db.session.query(Empleado.id, Empleado.nombre, Empleado.tipo_evaluacion).filter(
            Empleado.id.in_(empleado_ids)
        ).all()
        empleados_dict = {emp.id: {'nombre': emp.nombre, 'tipo_evaluacion': emp.tipo_evaluacion} for emp in empleados}
        
        # Consultar nombres de encargados
        encargados = db.session.query(Encargado.id, Encargado.nombre).filter(
            Encargado.id.in_(encargado_ids)
        ).all()
        encargados_dict = {enc.id: enc.nombre for enc in encargados}
        
        # Agrupar evaluaciones por empleado, fecha, encargado y tipo de evaluación
        # Modificado para manejar el caso especial de tipo_evaluacion=3
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            empleado_id = eval.empleado_id
            encargado_id = eval.encargado_id
            tipo_eval = eval.tipo_evaluacion  # Usar el tipo de evaluación del registro
            evaluaciones_agrupadas[empleado_id][fecha_str][encargado_id][tipo_eval].append(eval)

        # Calcular promedios para evaluaciones completas (considerando el tipo de evaluación)
        promedios_evaluaciones = {}  # (empleado_id, fecha, encargado_id, tipo_eval) -> promedio
        for empleado_id, fechas in evaluaciones_agrupadas.items():
            # Obtener el tipo de evaluación del empleado
            tipo_empleado = empleados_dict.get(empleado_id, {}).get('tipo_evaluacion', 1)  # Por defecto tipo 1
            
            for fecha, encargados in fechas.items():
                for encargado_id, tipos_eval in encargados.items():
                    # Procesar cada tipo de evaluación por separado
                    for tipo_eval, evals in tipos_eval.items():
                        # Determinar el número de aspectos requeridos según el tipo de evaluación
                        aspectos_requeridos = 8 if tipo_eval == 2 else 9
                        
                        # Determinar el divisor según el tipo de evaluación
                        divisor = 500  # Mantener 500 para ambos tipos como indicaste
                        
                        # Verificar si hay el número correcto de aspectos
                        if len(evals) == aspectos_requeridos:
                            # Sumar los porcentajes de todos los aspectos para esta evaluación
                            suma_porcentaje = sum(float(eval.porcentaje_total) for eval in evals)
                            # Calcular promedio (sobre 100%)
                            promedio = (suma_porcentaje / divisor) * 100
                            # Guardar el promedio
                            promedios_evaluaciones[(empleado_id, fecha, encargado_id, tipo_eval)] = round(promedio, 2)

        # Preparar datos para exportación CSV
        datos_exportacion = []
        
        if agrupar:
            # Exportar evaluaciones agrupadas (1 fila por evaluación completa)
            for empleado_id, fechas in evaluaciones_agrupadas.items():
                # Obtener el tipo de evaluación del empleado
                tipo_empleado = empleados_dict.get(empleado_id, {}).get('tipo_evaluacion', 1)  # Por defecto tipo 1
                
                for fecha, encargados in fechas.items():
                    for encargado_id, tipos_eval in encargados.items():
                        # Procesar cada tipo de evaluación por separado
                        for tipo_eval, evals in tipos_eval.items():
                            # Determinar el número de aspectos requeridos según el tipo de evaluación
                            aspectos_requeridos = 8 if tipo_eval == 2 else 9
                            
                            # Solo incluir evaluaciones completas
                            if len(evals) == aspectos_requeridos:
                                # Calcular promedio
                                promedio = promedios_evaluaciones.get((empleado_id, fecha, encargado_id, tipo_eval), 0)
                                
                                # Verificar si hay ausencia
                                ausente = any(eval.ausente for eval in evals)
                                
                                # Verificar si está a tiempo
                                a_tiempo = all(eval.a_tiempo for eval in evals)
                                
                                # Obtener comentarios (normalmente son iguales para todos los aspectos)
                                comentarios = evals[0].comentarios if evals else ""
                                
                                # Crear una fila para la evaluación completa
                                datos_exportacion.append({
                                    'Fecha': fecha,
                                    'Nombre Empleado': empleados_dict.get(empleado_id, {}).get('nombre', 'Desconocido'),
                                    'Nombre Encargado': encargados_dict.get(encargado_id, 'Desconocido'),
                                    'Calificación Promedio': promedio,
                                    'Comentarios': comentarios,
                                    'Tipo Evaluación': 'Administrativo' if tipo_eval == 2 else 'Operativo'
                                })
        else:
            # Exportar todos los aspectos individuales (formato original)
            for eval in evaluaciones:
                fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
                empleado_id = eval.empleado_id
                encargado_id = eval.encargado_id
                tipo_eval = eval.tipo_evaluacion
                
                # Obtener el promedio si existe (evaluación completa)
                promedio = promedios_evaluaciones.get((empleado_id, fecha_str, encargado_id, tipo_eval), None)
                
                datos_exportacion.append({
                    'Fecha': fecha_str,
                    'Nombre Empleado': empleados_dict.get(empleado_id, {}).get('nombre', 'Desconocido'),
                    'Nombre Encargado': encargados_dict.get(encargado_id, 'Desconocido'),
                    'Puntuación': eval.total_puntos,
                    'Porcentaje': eval.porcentaje_total,
                    'Promedio Evaluación': promedio if promedio is not None else 'N/A',
                    'Tipo Evaluación': 'Administrativo' if tipo_eval == 2 else 'Operativo'
                })
        
        # Formatear el periodo para la respuesta
        periodo_formateado = formatear_periodo(periodo, fecha_inicio)
        
        # Preparar respuesta con metadatos
        response_data = {
            'periodo': periodo_formateado,
            'rango_fechas': {
                'inicio': fecha_inicio.strftime('%Y-%m-%d'),
                'fin': fecha_fin.strftime('%Y-%m-%d')
            },
            'total_registros': len(datos_exportacion),
            'agrupado': agrupar,
            'datos': datos_exportacion
        }
        
        formato = request.args.get('formato', 'json')
        
        if formato.lower() == 'csv':
            # Generate CSV directly
            import csv
            import io
            
            # Create a string buffer for the CSV data
            output = io.StringIO()
            
            # Get field names from the first item
            if datos_exportacion:
                fieldnames = list(datos_exportacion[0].keys())
                
                # Create CSV writer
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                
                # Write header and rows
                writer.writeheader()
                writer.writerows(datos_exportacion)
                
                # Get the CSV data as a string
                csv_data = output.getvalue()
                
                # Create response with CSV data
                response = make_response(csv_data)
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = f'attachment; filename=evaluaciones_{periodo_formateado}.csv'
                
                return response
            else:
                return jsonify({'error': 'No hay datos para exportar'}), 404
        
        # If not CSV, return JSON as before
        response_data = {
            'periodo': periodo_formateado,
            'rango_fechas': {
                'inicio': fecha_inicio.strftime('%Y-%m-%d'),
                'fin': fecha_fin.strftime('%Y-%m-%d')
            },
            'total_registros': len(datos_exportacion),
            'agrupado': agrupar,
            'datos': datos_exportacion
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Error en exportación CSV: {str(e)}")
        return jsonify({'error': str(e)}), 500
        

def calcular_rango_fechas(periodo, fecha_seleccionada):
    """Calcula el rango de fechas basado en el periodo y la fecha seleccionada."""
    try:
        from dateutil.relativedelta import relativedelta
        
        if periodo == 'año':
            # Para año, usamos el año de la fecha_seleccionada
            año = fecha_seleccionada.year
            fecha_inicio = datetime(año, 1, 1)
            fecha_fin = datetime(año, 12, 31, 23, 59, 59)
            
        elif periodo == 'mes':
            # Para mes, usamos el año y mes de la fecha_seleccionada
            año = fecha_seleccionada.year
            mes = fecha_seleccionada.month
            fecha_inicio = datetime(año, mes, 1)
            
            # Último día del mes
            if mes == 12:
                fecha_fin = datetime(año + 1, 1, 1) - timedelta(seconds=1)
            else:
                fecha_fin = datetime(año, mes + 1, 1) - timedelta(seconds=1)
                
        elif periodo == 'semana':
            # Para semana, usamos la fecha_seleccionada directamente
            # que ya debe ser el primer día de la semana
            fecha_inicio = datetime.combine(fecha_seleccionada, datetime.min.time())
            # Último día de la semana (domingo)
            fecha_fin = fecha_inicio + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
        return fecha_inicio, fecha_fin
        
    except Exception as e:
        print(f"Error calculando rango de fechas: {e}")
        return None, None

def formatear_periodo(periodo, fecha_inicio):
    """Formatea el periodo para la respuesta según el tipo de periodo."""
    if periodo == 'año':
        return fecha_inicio.strftime('%Y')
    elif periodo == 'mes':
        return fecha_inicio.strftime('%Y-%m')
    elif periodo == 'semana':
        # ISO 8601 formato de semana: YYYY-Www
        año = fecha_inicio.isocalendar()[0]
        semana = fecha_inicio.isocalendar()[1]
        return f"{año}-W{semana:02d}"
    return ""


# ---------------------------------------------- EVALUACIONES POR EMPLEADO ------------------------------------------------------------------------------
@evaluacion_bp.route('/evaluaciones/empleado/<int:empleado_id>', methods=['OPTIONS', 'GET'])
def obtener_evaluaciones_empleado(empleado_id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Obtener parámetros de filtro con nuevos nombres
        encargado_id = request.args.get('encargado_id', type=int)  # ID del encargado
        periodo = request.args.get('periodo_tipo', 'mes')  # Valores posibles: 'month', 'week', 'year'
        periodo_valor = request.args.get('periodo_valor')  # Puede ser "3" para marzo, "2024-03", "15" para semana, etc.
        current_year = datetime.now().year
        
        # Validar que el empleado existe
        empleado = Empleado.query.get(empleado_id)
        if not empleado:
            return jsonify({'error': 'Empleado no encontrado'}), 404
        
        # Obtener el tipo de evaluación del empleado
        tipo_evaluacion = empleado.tipo_evaluacion
        
        # Mapear periodo a español
        periodo_mapeado = {
            'month': 'mes',
            'year': 'año',
            'week': 'semana',
            'mes': 'mes',
            'año': 'año',
            'semana': 'semana'
        }.get(periodo, None)

        if not periodo_mapeado:
            return jsonify({'error': 'Periodo no válido. Use "month", "year" o "week".'}), 400
            
        # Generar fecha_seleccionada según el periodo
        try:
            if periodo_mapeado == 'mes':
                if periodo_valor and periodo_valor.isdigit() and '-' not in periodo_valor:
                    year = current_year
                    month = int(periodo_valor)
                    fecha_seleccionada = date(year, month, 1)
                else:
                    try:
                        year, month = map(int, periodo_valor.split('-'))
                        fecha_seleccionada = date(year, month, 1)
                    except (ValueError, AttributeError):
                        raise ValueError(f"Formato de mes inválido: {periodo_valor}. Use MM o YYYY-MM")
                fecha_inicio, fecha_fin = calcular_rango_fechas(periodo_mapeado, fecha_seleccionada)
                query = Evaluacion.query.filter(
                    Evaluacion.empleado_id == empleado_id,
                    Evaluacion.fecha_evaluacion >= fecha_inicio,
                    Evaluacion.fecha_evaluacion <= fecha_fin
                )
            elif periodo_mapeado == 'año':
                year = int(periodo_valor)
                fecha_seleccionada = date(year, 1, 1)
                fecha_inicio, fecha_fin = calcular_rango_fechas(periodo_mapeado, fecha_seleccionada)
                query = Evaluacion.query.filter(
                    Evaluacion.empleado_id == empleado_id,
                    Evaluacion.fecha_evaluacion >= fecha_inicio,
                    Evaluacion.fecha_evaluacion <= fecha_fin
                )
            elif periodo_mapeado == 'semana':
                # SOLO filtra por num_semana y año actual, no uses fechas
                week = int(periodo_valor)
                fecha_seleccionada = datetime.fromisocalendar(current_year, week, 1).date()
                query = Evaluacion.query.filter(
                    Evaluacion.empleado_id == empleado_id,
                    Evaluacion.num_semana == week,
                    db.extract('year', Evaluacion.fecha_evaluacion) == current_year
                )
                fecha_inicio = None
                fecha_fin = None
        except ValueError as e:
            hoy = datetime.now()
            fecha_seleccionada = date(hoy.year, hoy.month, 1)
            periodo_mapeado = 'mes'
            fecha_inicio, fecha_fin = calcular_rango_fechas(periodo_mapeado, fecha_seleccionada)
            query = Evaluacion.query.filter(
                Evaluacion.empleado_id == empleado_id,
                Evaluacion.fecha_evaluacion >= fecha_inicio,
                Evaluacion.fecha_evaluacion <= fecha_fin
            )
        
                # Agregar filtro por encargado si se proporciona
        if encargado_id:
            query = query.filter(Evaluacion.encargado_id == encargado_id)

        # Ejecutar la consulta
        evaluaciones = query.order_by(Evaluacion.fecha_evaluacion.desc()).all()
        
        if not evaluaciones:
            return jsonify({
                'empleado_id': empleado_id,
                'empleado_nombre': empleado.nombre,
                'tipo_evaluacion': tipo_evaluacion,
                'periodo': formatear_periodo(periodo_mapeado, fecha_seleccionada),
                'num Semana': week,
                'rango_fechas': {
                    'inicio': fecha_inicio.strftime('%Y-%m-%d'),
                    'fin': fecha_fin.strftime('%Y-%m-%d')
                },
                'message': 'No hay evaluaciones para este empleado en el período seleccionado',
                'evaluaciones': []
            }), 200
        
        # Determinar el número de aspectos según el tipo de evaluación
        num_aspectos_esperados = 9 if tipo_evaluacion == 1 else 8
        divisor_calificacion = 500 if tipo_evaluacion == 1 else 500
        
        # Agrupar evaluaciones por fecha y encargado
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        for eval in evaluaciones:
            # Check if fecha_evaluacion is a datetime or date object
            fecha_local = eval.fecha_evaluacion
            if isinstance(fecha_local, datetime):
                # Only try to handle timezone if it's a datetime object
                if fecha_local.tzinfo is not None:
                    # If the date has timezone info, convert to local timezone
                    fecha_local = fecha_local.astimezone(pytz.timezone('America/Mexico_City'))
            
            # Format the date as string
            fecha_str = fecha_local.strftime('%Y-%m-%d')
            encargado_id = eval.encargado_id
            evaluaciones_agrupadas[fecha_str][encargado_id].append(eval)
        
        # Obtener información de encargados
        encargado_ids = {eval.encargado_id for eval in evaluaciones}
        encargados = Encargado.query.filter(Encargado.id.in_(encargado_ids)).all()
        encargados_dict = {enc.id: enc.nombre for enc in encargados}
        
        # Procesar resultados
        resultados = []
        for fecha, encargados_eval in evaluaciones_agrupadas.items():
            for encargado_id, evals in encargados_eval.items():
                # Verificar si hay alguna evaluación con ausente=1
                ausente = any(eval.ausente == 1 for eval in evals)
                
                # Si está ausente, no procesamos los aspectos
                if ausente:
                    resultados.append({
                        'fecha': fecha,
                        'encargado_id': encargado_id,
                        'encargado_nombre': encargados_dict.get(encargado_id, 'Desconocido'),
                        'ausente': True,
                        'comentarios': evals[0].comentarios if evals else '',
                        'calificacion_total': 0,
                        'aspectos': []
                    })
                else:
                    # Procesar aspectos para evaluaciones donde el empleado estuvo presente
                    aspectos = []
                    suma_porcentaje = 0
                    
                    for eval in evals:
                        aspectos.append({
                            'aspecto': eval.aspecto,
                            'calificacion': eval.total_puntos,
                            'porcentaje': eval.porcentaje_total
                        })
                        suma_porcentaje += float(eval.porcentaje_total)
                    
                    # Determinar el tipo de evaluación hecha (no la del empleado)
                    primer_eval = evals[0] if evals else None
                    tipo_eval_real = primer_eval.tipo_evaluacion if primer_eval else 1

                    # Definir aspectos esperados según tipo real hecho
                    aspectos_esperados = 9 if tipo_eval_real == 1 else 8
                    divisor = 500  # Mismo divisor para ambos

                    if len(evals) == aspectos_esperados:
                        calificacion_total = (suma_porcentaje / divisor) * 100
                    else:
                        calificacion_total = 0


                    
                    resultados.append({
                        'fecha': fecha,
                        'encargado_id': encargado_id,
                        'encargado_nombre': encargados_dict.get(encargado_id, 'Desconocido'),
                        'ausente': False,
                        'comentarios': evals[0].comentarios if evals else '',
                        'calificacion_total': round(calificacion_total, 2),
                        'aspectos': aspectos
                    })
        
        # Formatear el periodo para la respuesta
        periodo_formateado = formatear_periodo(periodo_mapeado, fecha_seleccionada)
        
      # Al armar la respuesta final:
        response = {
            'empleado_id': empleado_id,
            'empleado_nombre': empleado.nombre,
            'tipo_evaluacion': tipo_evaluacion,
            'periodo': periodo_formateado,
            'evaluaciones': resultados
        }
        if periodo_mapeado != 'semana':
            response['rango_fechas'] = {
                'inicio': fecha_inicio.strftime('%Y-%m-%d'),
                'fin': fecha_fin.strftime('%Y-%m-%d')
            }
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@evaluacion_bp.route('/evaluaciones-temporales', methods=['OPTIONS', 'POST'])
def guardar_evaluacion_temporal():
    if request.method == 'OPTIONS':
        return '', 200  # Respuesta correcta al preflight
    
    data = request.get_json(force=True)

    id_encargado = data.get('id_encargado')
    num_semana = data.get('num_semana')
    dato = data.get('dato')

    if id_encargado is None or num_semana is None or dato is None:
        return jsonify({'error': 'Faltan datos requeridos'}), 400

    try:
        # Buscar si ya existe una evaluación temporal con ese id_encargado y num_semana
        evaluacion_existente = EvaluacionTemporal.query.filter_by(
            id_encargado=id_encargado,
            num_semana=num_semana
        ).first()

        if evaluacion_existente:
            # Si existe, actualizamos el campo "dato"
            evaluacion_existente.dato = dato
            mensaje = 'Evaluación temporal actualizada con éxito'
        else:
            # Si no existe, la creamos
            nueva_eval = EvaluacionTemporal(
                id_encargado=id_encargado,
                num_semana=num_semana,
                dato=dato
            )
            db.session.add(nueva_eval)
            mensaje = 'Evaluación temporal guardada con éxito'

        db.session.commit()
        return jsonify({'mensaje': mensaje}), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Error de integridad. ¿Duplicado?'}), 409

    except Exception as e:
        db.session.rollback()
        print('Error:', e)
        return jsonify({'error': 'Error en el servidor'}), 500


@evaluacion_bp.route('/buscar-evaluaciones-temporales', methods=['OPTIONS', 'GET'])
def buscar_evaluaciones_temporales():
    id_encargado = request.args.get('id_encargado')
    num_semana = request.args.get('num_semana', type=int)

    if not id_encargado or num_semana is None:
        return jsonify({'error': 'Faltan datos requeridos'}), 400

    try:
        evaluacion = EvaluacionTemporal.query.filter_by(
            id_encargado=id_encargado,
            num_semana=num_semana
        ).first()

        if evaluacion:
            return jsonify({
                'id': evaluacion.id,
                'id_encargado': evaluacion.id_encargado,
                'num_semana': evaluacion.num_semana,
                'dato': evaluacion.dato
            }), 200
        else:
            return jsonify({}), 200  # No se encontró la evaluación

    except Exception as e:
        print("Error al buscar evaluación:", e)
        return jsonify({'error': 'Error del servidor'}), 500

@evaluacion_bp.route('/eliminar/evaluacion-temporal', methods=['OPTIONS', 'POST'])
def eliminar_evaluacion_temporal():
    data = request.get_json(force=True)

    id_encargado = data.get('id_encargado')
    num_semana = data.get('num_semana')

    if id_encargado is None or num_semana is None:
        return jsonify({'error': 'Faltan datos requeridos'}), 400

    try:
        # Buscar si existe esa evaluación temporal
        evaluacion = EvaluacionTemporal.query.filter_by(
            id_encargado=id_encargado,
            num_semana=num_semana
        ).first()

        if evaluacion:
            db.session.delete(evaluacion)
            db.session.commit()
            return jsonify({'mensaje': 'Evaluación temporal eliminada con éxito'}), 200
        else:
            return jsonify({'mensaje': 'No se encontró la evaluación temporal'}), 404

    except Exception as e:
        db.session.rollback()
        print('Error:', e)
        return jsonify({'error': 'Error en el servidor'}), 500

@evaluacion_bp.route('/buscar/evaluacion-existente', methods=['OPTIONS', 'GET'])
def buscar_evaluacion_existente():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        # Obtener los parámetros desde la URL (query params)
        id_encargado = request.args.get('id_encargado', type=int)
        num_semana = request.args.get('num_semana', type=int)

        # Validación
        if id_encargado is None or num_semana is None:
            return jsonify({'error': 'Faltan parámetros requeridos'}), 400

        # Buscar si existe al menos una evaluación con esos datos
        existe = Evaluacion.query.filter_by(
            encargado_id=id_encargado,
            num_semana=num_semana
        ).first()

        if existe:
            return jsonify({'existe': True}), 200
        else:
            return jsonify({'existe': False}), 200

    except Exception as e:
        print(f"Error al buscar evaluación: {e}")
        return jsonify({'error': 'Error en el servidor'}), 500


    
