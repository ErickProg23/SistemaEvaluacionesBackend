from flask import Blueprint, make_response, request, jsonify
from app.models import  Encargado, Evaluacion_Encargado
from app import db
from collections import defaultdict
from datetime import datetime, date, timedelta


retroalimentacion_bp = Blueprint('retroalimentacion_bp', __name__)

@retroalimentacion_bp.route('/<int:usuario_id>', methods=['GET', 'OPTIONS'])
def obtener_retroalimentacion_encargado(usuario_id):
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Primero buscar el encargado por usuario_id para obtener el encargado_id
        encargado = Encargado.query.filter(
            Encargado.usuario_id == usuario_id
        ).first()
        
        if not encargado:
            return jsonify({
                'message': 'No se encontró un encargado asociado a este usuario',
                'evaluaciones': []
            }), 404
        
        # Ahora consultar las evaluaciones usando el encargado_id obtenido
        evaluaciones = Evaluacion_Encargado.query.filter(
            Evaluacion_Encargado.encargado_id == encargado.id
        ).order_by(
            Evaluacion_Encargado.fecha_evaluacion.desc()
        ).all()
        
        if not evaluaciones:
            return jsonify({
                'message': 'No se encontraron evaluaciones para este encargado',
                'evaluaciones': []
            }), 200
        
        # Agrupar evaluaciones por fecha para obtener solo las más recientes
        evaluaciones_agrupadas = defaultdict(list)
        for eval in evaluaciones:
            fecha_str = eval.fecha_evaluacion.strftime('%Y-%m-%d')
            evaluaciones_agrupadas[fecha_str].append(eval)
        
        # Obtener solo las evaluaciones de la fecha más reciente
        fecha_mas_reciente = max(evaluaciones_agrupadas.keys())
        evaluaciones_recientes = evaluaciones_agrupadas[fecha_mas_reciente]
        
        # Calcular la calificación total
        suma_porcentajes = sum(float(eval.porcentaje_total) for eval in evaluaciones_recientes)
        calificacion_total = (suma_porcentajes * 100) / 500
        # Limitar a 100% máximo
        calificacion_total = min(calificacion_total, 100.0)
        
        # Formatear los datos para la respuesta
        evaluaciones_formateadas = []
        for eval in evaluaciones_recientes:
            evaluaciones_formateadas.append({
                'id': eval.id,
                'encargado_id': eval.encargado_id,
                'usuario_id': eval.usuario_id,
                'fecha_evaluacion': eval.fecha_evaluacion.strftime('%Y-%m-%d'),
                'total_puntos': float(eval.total_puntos),
                'porcentaje_total': float(eval.porcentaje_total),
                'comentarios': eval.comentarios,
                'aspecto': eval.aspecto,
                'ausente': eval.ausente,
                'a_tiempo': eval.a_tiempo,
                'num_semana': eval.num_semana,
                'tipo_evaluacion': eval.tipo_evaluacion
            })
        
        return jsonify({
            'usuario_id': usuario_id,
            'encargado_id': encargado.id,
            'encargado_nombre': encargado.nombre,
            'fecha_mas_reciente': fecha_mas_reciente,
            'total_evaluaciones': len(evaluaciones_formateadas),
            'calificacion_total': round(calificacion_total, 2),
            'suma_porcentajes': round(suma_porcentajes, 2),
            'evaluaciones': evaluaciones_formateadas
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Error al obtener las evaluaciones: {str(e)}'
        }), 500