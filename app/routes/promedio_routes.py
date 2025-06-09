from flask import Blueprint, request, jsonify
from app.models import Empleado, Encargado, Usuario, Evaluacion
from app import db
from collections import defaultdict


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
        
        # Consultar nombres e información de encargados
        encargados = Encargado.query.filter(Encargado.id.in_(encargado_ids)).all()
        encargados_dict = {enc.id: {
            'nombre': enc.nombre,
            'tipo_evaluacion': enc.tipo_evaluacion
        } for enc in encargados}
        
        # Agrupar evaluaciones por encargado y fecha
        evaluaciones_agrupadas = defaultdict(lambda: defaultdict(list))
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            encargado_id = eval.encargado_id
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
                    divisor = 400  # Para tipo 2 (8 aspectos)
                
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