from flask import Blueprint, request, jsonify
from app.models import Empleado, Encargado, Usuario, Evaluacion, Evaluacion_Encargado
from app import db
from collections import defaultdict
from datetime import datetime, date


# Definición del Blueprint para las rutas de obtención de datos
prom_bp = Blueprint('prom_bp', __name__)



# --------------- OBTENER PROMEDIO POR ENCARGADO ----------------------------------------------------------
@prom_bp.route('/evaluaciones/promedio-encargados', methods=['OPTIONS', 'GET'])
def obtener_promedio_encargados():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Obtener todas las evaluaciones (incluyendo ausentes)
        evaluaciones = Evaluacion.query.all()
        
        if not evaluaciones:
            return jsonify({'error': 'No hay evaluaciones disponibles'}), 404
        
        # Obtener IDs de encargados únicos
        encargado_ids = {eval.encargado_id for eval in evaluaciones}
        
        # Consultar nombres e información de encargados (solo activos)
        encargados = Encargado.query.filter(Encargado.id.in_(encargado_ids), Encargado.activo == True).all()
        active_encargado_ids = {enc.id for enc in encargados}
        encargados_dict = {enc.id: {
            'nombre': enc.nombre,
            'tipo_evaluacion': enc.tipo_evaluacion
        } for enc in encargados}
        
        # Agrupar evaluaciones por encargado y fecha (solo encargados activos)
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            encargado_id = eval.encargado_id
            if encargado_id in active_encargado_ids:
                evaluaciones_agrupadas[encargado_id][fecha_str].append(eval)
        
        # Procesar datos por encargado
        resultados_encargados = defaultdict(lambda: {
            'suma_porcentaje_total': 0.0,
            'total_evaluaciones_completas': 0,
            'nombre': 'Nombre no encontrado',
            'total_empleados_evaluados': set(),
            'tipo_evaluacion': 0
        })
        
        # Contar evaluaciones completas y sumar porcentajes según el tipo de encargado
        for encargado_id, fechas in evaluaciones_agrupadas.items():
            # Obtener el tipo de evaluación del encargado
            tipo_encargado = encargados_dict.get(encargado_id, {}).get('tipo_evaluacion', 0)
            resultados_encargados[encargado_id]['tipo_evaluacion'] = tipo_encargado
            resultados_encargados[encargado_id]['nombre'] = encargados_dict.get(encargado_id, {}).get('nombre', 'Nombre no encontrado')
            
            for fecha, evals in fechas.items():
                # Filtrar evaluaciones donde ausente=0 (no ausentes)
                evals_presentes = [e for e in evals if e.ausente == 0]
                
                if not evals_presentes:
                    continue  # Si todas las evaluaciones son de ausentes, saltamos
                
                # Agrupar por empleado para verificar evaluaciones completas
                empleados_evaluados = {}
                for eval in evals_presentes:
                    if eval.empleado_id not in empleados_evaluados:
                        empleados_evaluados[eval.empleado_id] = []
                    empleados_evaluados[eval.empleado_id].append(eval)
                
                # Verificar evaluaciones completas por empleado
                for empleado_id, evals_empleado in empleados_evaluados.items():
                    # Determinar si la evaluación está completa según el tipo de encargado
                    es_completa = False
                    aspectos_requeridos = 9 if tipo_encargado == 1 else 8
                    
                    if len(evals_empleado) == aspectos_requeridos:
                        es_completa = True
                    
                    if es_completa:
                        resultados_encargados[encargado_id]['total_evaluaciones_completas'] += 1
                        resultados_encargados[encargado_id]['total_empleados_evaluados'].add(empleado_id)
                        
                        # Sumar los porcentajes de todos los aspectos para esta evaluación
                        suma_porcentaje = sum(float(eval.porcentaje_total) for eval in evals_empleado)
                        resultados_encargados[encargado_id]['suma_porcentaje_total'] += suma_porcentaje
        
        # Calcular calificación promedio por encargado
        detalle_encargados = []
        for encargado_id, datos in resultados_encargados.items():
            if datos['total_evaluaciones_completas'] > 0:
                # Calcular el promedio según el tipo de encargado
                tipo_encargado = datos['tipo_evaluacion']
                divisor = 500  # Valor por defecto para tipo 1 (9 aspectos)
                
                if tipo_encargado == 2:
                    divisor = 500  # Para tipo 2 (8 aspectos)
                
                # Calcular el promedio de porcentaje final
                porcentaje_final = (datos['suma_porcentaje_total'] / (divisor * datos['total_evaluaciones_completas'])) * 100
                porcentaje_final = min(porcentaje_final, 100.0)  # Limitar a 100%
                
                detalle_encargados.append({
                    'encargado_id': encargado_id,
                    'nombre': datos['nombre'],
                    'tipo_evaluacion': tipo_encargado,
                    'calificacion_promedio': round(porcentaje_final, 2),
                    'total_evaluaciones': datos['total_evaluaciones_completas'],
                    'total_empleados_evaluados': len(datos['total_empleados_evaluados'])
                })
        
        # Ordenar por calificación promedio de mayor a menor
        detalle_encargados.sort(key=lambda x: x['calificacion_promedio'], reverse=True)
        
        # Calcular promedio general de todos los encargados
        if detalle_encargados:
            promedio_general = sum(enc['calificacion_promedio'] for enc in detalle_encargados) / len(detalle_encargados)
        else:
            promedio_general = 0
        
        # Preparar respuesta
        response_data = {
            'total_encargados': len(detalle_encargados),
            'promedio_general': round(promedio_general, 2),
            'detalle_encargados': detalle_encargados
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prom_bp.route('/evaluaciones/aspectos', methods=['OPTIONS', 'GET'])
def obtener_promedio_aspectos():
    try:
        # Consulta con tipo incluido
        query = db.text("""
            SELECT 
                p.texto AS aspecto,
                p.tipo AS tipo,
                COALESCE(ROUND((AVG(e.total_puntos) / 5) * 100, 2), 0.00) AS porcentaje
            FROM 
                aspecto p
            LEFT JOIN 
                evaluacion e ON p.texto = e.aspecto AND e.ausente = FALSE
            GROUP BY 
                p.id, p.texto, p.tipo
            ORDER BY 
                p.id;
        """)

        result = db.session.execute(query)
        data = [
            {
                "aspecto": row.aspecto,
                "tipo": row.tipo,
                "porcentaje": float(row.porcentaje)
            }
            for row in result
        ]

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@prom_bp.route('/evaluaciones/encargados-por-periodo', methods=['GET', 'OPTIONS'])
def obtener_encargados_por_periodo():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Obtener parámetros de la consulta
        periodo_tipo = request.args.get('periodo_tipo')  # 'month', 'week', 'year'
        periodo_valor = request.args.get('periodo_valor')  # valor del período
        usuario_id = request.args.get('usuario_id', type=int)  # opcional, para filtrar por usuario específico
        
        # Validar parámetros requeridos
        if not periodo_tipo or not periodo_valor:
            return jsonify({
                'error': 'Se requieren los parámetros periodo_tipo y periodo_valor'
            }), 400
            
        # Validar tipo de período
        if periodo_tipo not in ['month', 'week', 'year']:
            return jsonify({
                'error': 'periodo_tipo debe ser: month, week o year'
            }), 400
        
        # Construir consulta base usando Evaluacion_Encargado
        query = Evaluacion_Encargado.query
        
        # Aplicar filtros de período
        if periodo_tipo == 'week':
            try:
                semana = int(periodo_valor)
                query = query.filter(Evaluacion_Encargado.num_semana == semana)
            except ValueError:
                return jsonify({'error': 'periodo_valor debe ser un número para semana'}), 400
                
        elif periodo_tipo == 'month':
            try:
                mes = int(periodo_valor)
                query = query.filter(db.extract('month', Evaluacion_Encargado.fecha_evaluacion) == mes)
            except ValueError:
                return jsonify({'error': 'periodo_valor debe ser un número para mes'}), 400
                
        elif periodo_tipo == 'year':
            try:
                año = int(periodo_valor)
                query = query.filter(db.extract('year', Evaluacion_Encargado.fecha_evaluacion) == año)
            except ValueError:
                return jsonify({'error': 'periodo_valor debe ser un número para año'}), 400
        
        # Filtro opcional por usuario específico (buscar en encargado por usuario_id)
        if usuario_id:
            # Primero obtener el encargado_id correspondiente al usuario_id
            encargado = Encargado.query.filter(Encargado.usuario_id == usuario_id).first()
            if encargado:
                query = query.filter(Evaluacion_Encargado.encargado_id == encargado.id)
            else:
                return jsonify({
                    'mensaje': 'No se encontró un encargado asociado a este usuario',
                    'encargados': [],
                    'total_encargados': 0
                }), 404
        
        # Ejecutar consulta
        evaluaciones = query.all()
        
        if not evaluaciones:
            return jsonify({
                'mensaje': f'No se encontraron evaluaciones para {periodo_tipo}: {periodo_valor}',
                'encargados': [],
                'total_encargados': 0
            }), 200
        
        # Obtener IDs únicos de encargados
        encargado_ids = {eval.encargado_id for eval in evaluaciones}
        
        # Consultar información de encargados
        encargados = Encargado.query.filter(Encargado.id.in_(encargado_ids)).all()
        encargados_dict = {enc.id: {
            'nombre': enc.nombre,
            'tipo_evaluacion': enc.tipo_evaluacion,
            'activo': enc.activo,
            'usuario_id': enc.usuario_id
        } for enc in encargados}
        
        # Agrupar evaluaciones por encargado y fecha
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            encargado_id = eval.encargado_id
            evaluaciones_agrupadas[encargado_id][fecha_str].append(eval)
        
        # Procesar datos por encargado
        resultados_encargados = []
        
        for encargado_id, fechas in evaluaciones_agrupadas.items():
            encargado_info = encargados_dict.get(encargado_id, {
                'nombre': f'Encargado ID {encargado_id} (No encontrado)',
                'tipo_evaluacion': 1,
                'activo': False,
                'usuario_id': None
            })
            
            tipo_encargado = encargado_info.get('tipo_evaluacion', 1)
            total_evaluaciones_completas = 0
            suma_porcentaje_total = 0.0
            usuarios_evaluados = set()  # Cambié de empleados a usuarios ya que en evaluacion_encargado se evalúan usuarios
            fechas_evaluacion = set()
            
            for fecha, evals in fechas.items():
                fechas_evaluacion.add(fecha)
                
                # Filtrar evaluaciones donde ausente=0 (no ausentes)
                evals_presentes = [e for e in evals if e.ausente == 0]
                
                if not evals_presentes:
                    continue
                
                # Agrupar por usuario para verificar evaluaciones completas
                usuarios_por_fecha = {}
                for eval in evals_presentes:
                    if eval.usuario_id not in usuarios_por_fecha:
                        usuarios_por_fecha[eval.usuario_id] = []
                    usuarios_por_fecha[eval.usuario_id].append(eval)
                
                # Verificar evaluaciones completas por usuario
                for usuario_eval_id, evals_usuario in usuarios_por_fecha.items():
                    aspectos_requeridos = 9 if tipo_encargado == 1 else 8
                    
                    if len(evals_usuario) == aspectos_requeridos:
                        total_evaluaciones_completas += 1
                        usuarios_evaluados.add(usuario_eval_id)
                        
                        # Sumar los porcentajes de todos los aspectos
                        suma_porcentaje = sum(float(eval.porcentaje_total) for eval in evals_usuario)
                        suma_porcentaje_total += suma_porcentaje
            
            # Calcular calificación promedio
            if total_evaluaciones_completas > 0:
                divisor = 500  # Para ambos tipos
                porcentaje_final = (suma_porcentaje_total / (divisor * total_evaluaciones_completas)) * 100
                porcentaje_final = min(porcentaje_final, 100.0)
            else:
                porcentaje_final = 0.0
            
            resultados_encargados.append({
                'encargado_id': encargado_id,
                'usuario_id': encargado_info.get('usuario_id'),
                'nombre': encargado_info.get('nombre'),
                'tipo_evaluacion': tipo_encargado,
                'activo': encargado_info.get('activo'),
                'calificacion_promedio': round(porcentaje_final, 2),
                'total_evaluaciones_completas': total_evaluaciones_completas,
                'total_usuarios_evaluados': len(usuarios_evaluados),
                'fechas_evaluacion': sorted(list(fechas_evaluacion)),
                'periodo_consultado': {
                    'tipo': periodo_tipo,
                    'valor': periodo_valor
                }
            })
        
        # Ordenar por calificación promedio (mayor a menor)
        resultados_encargados.sort(key=lambda x: x['calificacion_promedio'], reverse=True)
        
        # Calcular estadísticas generales
        promedio_general = 0
        if resultados_encargados:
            promedio_general = sum(enc['calificacion_promedio'] for enc in resultados_encargados) / len(resultados_encargados)
        
        response_data = {
            'periodo_consultado': {
                'tipo': periodo_tipo,
                'valor': periodo_valor
            },
            'total_encargados': len(resultados_encargados),
            'promedio_general': round(promedio_general, 2),
            'encargados': resultados_encargados
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

@prom_bp.route('/evaluaciones/export-por-encargado', methods=['GET'])
def exportar_evaluaciones_por_encargado():
    """Servicio para extraer evaluaciones agrupadas por encargado con filtros de fecha (histórico)"""
    try:
        # Obtener parámetros de filtro
        periodo_tipo = request.args.get('periodo_tipo')  # 'mes', 'semana', 'año'
        periodo_valor = request.args.get('periodo_valor')  # valor del período
        
        # Validar parámetros requeridos
        if not periodo_tipo or not periodo_valor:
            return jsonify({
                'error': 'Se requieren los parámetros periodo_tipo y periodo_valor'
            }), 400
            
        # Validar tipo de período
        if periodo_tipo not in ['month', 'week', 'year']:
            return jsonify({
                'error': 'periodo_tipo debe ser: month, week o year'
            }), 400
            
        try:
            periodo_valor = int(periodo_valor)
        except ValueError:
            return jsonify({
                'error': 'periodo_valor debe ser un número entero'
            }), 400
        
        # Construir filtro de consulta según el tipo de período
        # IMPORTANTE: Solo filtramos por fecha y ausente, NO por relación actual
        if periodo_tipo == 'week':
            evaluaciones = Evaluacion.query.filter(
                Evaluacion.num_semana == periodo_valor,
            ).all()
        elif periodo_tipo == 'month':
            evaluaciones = Evaluacion.query.filter(
                db.extract('month', Evaluacion.fecha_evaluacion) == periodo_valor,
            ).all()
        elif periodo_tipo == 'year':
            evaluaciones = Evaluacion.query.filter(
                db.extract('year', Evaluacion.fecha_evaluacion) == periodo_valor,
            ).all()
        
        if not evaluaciones:
            return jsonify({
                'mensaje': f'No se encontraron evaluaciones para {periodo_tipo}: {periodo_valor}',
                'datos': []
            }), 200
        
        # Obtener IDs únicos de encargados y empleados DESDE LAS EVALUACIONES HISTÓRICAS
        encargado_ids = {eval.encargado_id for eval in evaluaciones}
        empleado_ids = {eval.empleado_id for eval in evaluaciones}
        
        # Consultar información de encargados y empleados
        # Incluir encargados que podrían estar inactivos pero que hicieron evaluaciones
        encargados = Encargado.query.filter(Encargado.id.in_(encargado_ids)).all()
        empleados = Empleado.query.filter(Empleado.id.in_(empleado_ids)).all()
        
        # Crear diccionarios para acceso rápido
        encargados_dict = {enc.id: {
            'nombre': enc.nombre,
            'tipo_evaluacion': enc.tipo_evaluacion,
            'activo': enc.activo
        } for enc in encargados}
        
        empleados_dict = {emp.id: {
            'nombre': emp.nombre,
            'num_empleado': emp.num_empleado,
            'tipo_evaluacion': emp.tipo_evaluacion,
            'activo': emp.activo
        } for emp in empleados}
        
        # Agrupar evaluaciones por encargado QUE REALMENTE HIZO LA EVALUACIÓN
        # y por empleado que fue evaluado EN ESE MOMENTO
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        for eval in evaluaciones:
            # Usar el encargado_id de la evaluación (histórico)
            encargado_historico = eval.encargado_id
            empleado_evaluado = eval.empleado_id
            evaluaciones_agrupadas[encargado_historico][empleado_evaluado].append(eval)
        
        # Procesar datos por encargado histórico
        resultados_finales = []
        
        for encargado_id, empleados_evaluaciones in evaluaciones_agrupadas.items():
            encargado_info = encargados_dict.get(encargado_id, {
                'nombre': f'Encargado ID {encargado_id} (No encontrado)',
                'tipo_evaluacion': 1,
                'activo': False
            })
            
            # Lista de empleados con sus calificaciones para este encargado
            empleados_calificaciones = []
            
            for empleado_id, evals_empleado in empleados_evaluaciones.items():
                empleado_info = empleados_dict.get(empleado_id, {
                    'nombre': f'Empleado ID {empleado_id} (No encontrado)',
                    'num_empleado': empleado_id,
                    'tipo_evaluacion': 1,
                    'activo': False
                })
                
                # Separar evaluaciones por estado de ausencia
                evals_presentes = [e for e in evals_empleado if e.ausente == 0]
                evals_ausentes = [e for e in evals_empleado if e.ausente == 1]
                
                # Determinar si el empleado estuvo ausente
                estuvo_ausente = len(evals_ausentes) > 0
                total_dias_ausente = len(evals_ausentes)
                total_dias_presente = len(evals_presentes)
                
                # Calcular calificación solo con evaluaciones presentes
                if len(evals_presentes) > 0:
                    tipo_evaluacion_empleado = empleado_info.get('tipo_evaluacion', 1)
                    
                    if tipo_evaluacion_empleado == 3:
                        # Para empleados tipo 3, procesar ambos tipos de evaluación
                        evals_tipo_1 = [e for e in evals_presentes if e.tipo_evaluacion == 1]
                        evals_tipo_2 = [e for e in evals_presentes if e.tipo_evaluacion == 2]
                        
                        calificaciones_empleado = []
                        
                        # Procesar evaluaciones tipo 1
                        if evals_tipo_1:
                            suma_porcentaje_1 = sum(float(e.porcentaje_total) for e in evals_tipo_1)
                            calificacion_1 = (suma_porcentaje_1 / (len(evals_tipo_1) * 55.56)) * 100
                            calificaciones_empleado.append(min(calificacion_1, 100.0))
                        
                        # Procesar evaluaciones tipo 2
                        if evals_tipo_2:
                            suma_porcentaje_2 = sum(float(e.porcentaje_total) for e in evals_tipo_2)
                            calificacion_2 = (suma_porcentaje_2 / (len(evals_tipo_2) * 62.5)) * 100
                            calificaciones_empleado.append(min(calificacion_2, 100.0))
                        
                        # Promedio de ambas calificaciones si existen
                        if calificaciones_empleado:
                            calificacion_promedio = sum(calificaciones_empleado) / len(calificaciones_empleado)
                        else:
                            calificacion_promedio = 0.0
                            
                    else:
                        # Para empleados tipo 1 o 2
                        suma_porcentaje = sum(float(e.porcentaje_total) for e in evals_presentes)
                        
                        if tipo_evaluacion_empleado == 1:
                            promedio_por_aspecto = suma_porcentaje / len(evals_presentes)
                            calificacion_promedio = (promedio_por_aspecto / 55.56) * 100
                        else:
                            promedio_por_aspecto = suma_porcentaje / len(evals_presentes)
                            calificacion_promedio = (promedio_por_aspecto / 62.5) * 100
                        
                        calificacion_promedio = min(calificacion_promedio, 100.0)
                else:
                    # Si solo tiene evaluaciones de ausente, calificación 0
                    calificacion_promedio = 0.0
                    tipo_evaluacion_empleado = empleado_info.get('tipo_evaluacion', 1)
                
                # Determinar estado del empleado
                if estuvo_ausente and len(evals_presentes) == 0:
                    estado_empleado = "AUSENTE"
                    estado_detalle = f"Ausente todos los dias ({total_dias_ausente} dias)"
                elif estuvo_ausente and len(evals_presentes) > 0:
                    estado_empleado = "PARCIALMENTE_AUSENTE"
                    estado_detalle = f"Presente {total_dias_presente} dias, ausente {total_dias_ausente} dias"
                else:
                    estado_empleado = "PRESENTE"
                    estado_detalle = f"Presente todos los dias ({total_dias_presente} dias)"
                
                # Agregar empleado a la lista (TODOS, ausentes y presentes)
                empleados_calificaciones.append({
                    'num_empleado': empleado_info.get('num_empleado', 'N/A'),
                    'nombre': empleado_info.get('nombre', 'Nombre no encontrado'),
                    'calificacion': round(calificacion_promedio, 2),
                    'tipo_evaluacion': tipo_evaluacion_empleado,
                    'total_evaluaciones': len(evals_empleado),
                    'evaluaciones_presentes': len(evals_presentes),
                    'evaluaciones_ausentes': len(evals_ausentes),
                    'estado_asistencia': estado_empleado,
                    'detalle_asistencia': estado_detalle,
                    'estuvo_ausente': estuvo_ausente,
                    'empleado_activo_actual': empleado_info.get('activo', False),
                    'fecha_evaluaciones': [eval.fecha_evaluacion.strftime('%Y-%m-%d') for eval in evals_empleado[:3]]
                })
            
            # Solo incluir encargados que tengan empleados con evaluaciones válidas
            if empleados_calificaciones:
                # Ordenar empleados por calificación (mayor a menor)
                empleados_calificaciones.sort(key=lambda x: x['calificacion'], reverse=True)
                
                resultados_finales.append({
                    'encargado_id': encargado_id,
                    'encargado_nombre': encargado_info.get('nombre', 'Nombre no encontrado'),
                    'encargado_activo_actual': encargado_info.get('activo', False),
                    'total_empleados': len(empleados_calificaciones),
                    'empleados': empleados_calificaciones
                })
        
        # Ordenar encargados por número de empleados evaluados (mayor a menor)
        resultados_finales.sort(key=lambda x: x['total_empleados'], reverse=True)
        
        # Preparar respuesta final
        response_data = {
            'filtro_aplicado': {
                'tipo': periodo_tipo,
                'valor': periodo_valor
            },
            'total_encargados': len(resultados_finales),
            'total_empleados_evaluados': sum(enc['total_empleados'] for enc in resultados_finales),
            'nota': 'Este reporte muestra las evaluaciones históricas según quién realmente evaluó a cada empleado en el período especificado',
            'datos': resultados_finales
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

@prom_bp.route('/evaluaciones/aspectos-por-encargado', methods=['GET', 'OPTIONS'])
def obtener_aspectos_por_encargado():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Obtener parámetros de la consulta
        encargado_id = request.args.get('encargado_id', type=int)
        periodo_tipo = request.args.get('periodo_tipo')  # 'month', 'week', 'year'
        periodo_valor = request.args.get('periodo_valor')  # valor del período
        
        # Validar parámetros requeridos
        if not encargado_id:
            return jsonify({
                'error': 'Se requiere el parámetro encargado_id'
            }), 400
            
        if not periodo_tipo or not periodo_valor:
            return jsonify({
                'error': 'Se requieren los parámetros periodo_tipo y periodo_valor'
            }), 400
            
        # Validar tipo de período
        if periodo_tipo not in ['month', 'week', 'year']:
            return jsonify({
                'error': 'periodo_tipo debe ser: month, week o year'
            }), 400
        
        # Verificar que el encargado existe
        encargado = Encargado.query.get(encargado_id)
        if not encargado:
            return jsonify({
                'error': 'Encargado no encontrado'
            }), 404
        
        # Construir consulta base usando Evaluacion_Encargado
        query = Evaluacion_Encargado.query.filter(
            Evaluacion_Encargado.encargado_id == encargado_id,
            Evaluacion_Encargado.ausente == False  # Solo evaluaciones presentes
        )
        
        # Aplicar filtros de período
        if periodo_tipo == 'week':
            try:
                semana = int(periodo_valor)
                query = query.filter(Evaluacion_Encargado.num_semana == semana)
            except ValueError:
                return jsonify({'error': 'periodo_valor debe ser un número para semana'}), 400
                
        elif periodo_tipo == 'month':
            try:
                mes = int(periodo_valor)
                query = query.filter(db.extract('month', Evaluacion_Encargado.fecha_evaluacion) == mes)
            except ValueError:
                return jsonify({'error': 'periodo_valor debe ser un número para mes'}), 400
                
        elif periodo_tipo == 'year':
            try:
                año = int(periodo_valor)
                query = query.filter(db.extract('year', Evaluacion_Encargado.fecha_evaluacion) == año)
            except ValueError:
                return jsonify({'error': 'periodo_valor debe ser un número para año'}), 400
        
        # Ejecutar consulta
        evaluaciones = query.all()
        
        if not evaluaciones:
            return jsonify({
                'mensaje': f'No se encontraron evaluaciones para el encargado en {periodo_tipo}: {periodo_valor}',
                'encargado_id': encargado_id,
                'encargado_nombre': encargado.nombre,
                'aspectos': [],
                'calificacion_total': 0.0,
                'total_evaluaciones': 0
            }), 200
        
        # Agrupar evaluaciones por aspecto
        aspectos_agrupados = defaultdict(list)
        for eval in evaluaciones:
            aspectos_agrupados[eval.aspecto].append(eval)
        
        # Procesar aspectos según el tipo de período
        aspectos_resultado = []
        suma_total_porcentajes = 0.0
        
        for aspecto, evals_aspecto in aspectos_agrupados.items():
            if periodo_tipo == 'week':
                # Para semana: tomar la evaluación más reciente (debería ser única)
                eval_reciente = max(evals_aspecto, key=lambda x: x.fecha_evaluacion)
                
                aspecto_data = {
                    'aspecto': aspecto,
                    'puntos': float(eval_reciente.total_puntos),
                    'porcentaje': float(eval_reciente.porcentaje_total),
                    'comentarios': eval_reciente.comentarios or '',
                    'fecha': eval_reciente.fecha_evaluacion.strftime('%Y-%m-%d')
                }
                suma_total_porcentajes += float(eval_reciente.porcentaje_total)
                
            else:
                # Para mes/año: calcular promedio
                total_puntos = sum(float(eval.total_puntos) for eval in evals_aspecto)
                total_porcentaje = sum(float(eval.porcentaje_total) for eval in evals_aspecto)
                num_evaluaciones = len(evals_aspecto)
                
                promedio_puntos = total_puntos / num_evaluaciones
                promedio_porcentaje = total_porcentaje / num_evaluaciones
                
                # Concatenar comentarios únicos (no vacíos)
                comentarios_unicos = list(set([
                    eval.comentarios for eval in evals_aspecto 
                    if eval.comentarios and eval.comentarios.strip()
                ]))
                comentarios_texto = ' | '.join(comentarios_unicos) if comentarios_unicos else ''
                
                aspecto_data = {
                    'aspecto': aspecto,
                    'puntos': round(promedio_puntos, 2),
                    'porcentaje': round(promedio_porcentaje, 2),
                    'comentarios': comentarios_texto,
                    'num_evaluaciones': num_evaluaciones,
                    'fechas': [eval.fecha_evaluacion.strftime('%Y-%m-%d') for eval in evals_aspecto]
                }
                suma_total_porcentajes += promedio_porcentaje
            
            aspectos_resultado.append(aspecto_data)
        
        # Calcular calificación total usando la fórmula correcta
        calificacion_total = (suma_total_porcentajes * 100) / 500
        calificacion_total = min(calificacion_total, 100.0)  # Limitar a 100%
        
        # Ordenar aspectos por porcentaje (mayor a menor)
        aspectos_resultado.sort(key=lambda x: x['porcentaje'], reverse=True)
        
        return jsonify({
            'encargado_id': encargado_id,
            'encargado_nombre': encargado.nombre,
            'tipo_evaluacion': encargado.tipo_evaluacion,
            'periodo_tipo': periodo_tipo,
            'periodo_valor': periodo_valor,
            'calificacion_total': round(calificacion_total, 2),
            'suma_porcentajes': round(suma_total_porcentajes, 2),
            'total_aspectos': len(aspectos_resultado),
            'aspectos': aspectos_resultado
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Error al obtener aspectos por encargado: {str(e)}'
        }), 500