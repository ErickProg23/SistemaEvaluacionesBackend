from datetime import datetime
from io import BytesIO
import os
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from flask import Blueprint, make_response, render_template, request, jsonify, send_file, send_from_directory
from app.models import Empleado, Encargado, Formato, Usuario
from weasyprint import HTML, CSS


# Definición del Blueprint para las rutas de obtención de datos
formato_bp = Blueprint('formato_bp', __name__)



# NUEVA RUTA PARA OBTENER TODOS LOS FORMATOS ----------------------------------------------------------
@formato_bp.route('/formatos', methods=['OPTIONS', 'GET'])
def obtener_formatos():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        formatos = Formato.query.all()
        
        if not formatos:
            return jsonify({'message': 'No hay formatos disponibles'}), 404
        
        formatos_data = []
        for formato in formatos:
            formato_data = {
                'id': formato.id,
                'nombre': formato.nombre,
                'descripcion': formato.descripcion,
                'archivo_url': formato.archivo_url,
                'fecha_subida': formato.fecha_subida.strftime('%Y-%m-%d %H:%M:%S')
            }
            formatos_data.append(formato_data)
        
        return jsonify({
            'total': len(formatos_data),
            'formatos': formatos_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------- DESCARGAR FORMATO ----------------------------------------------------------
@formato_bp.route('/formatos/download/<int:formato_id>', methods=['GET'])
def download_formato(formato_id):
    try:
        formato = Formato.query.get(formato_id)
        if not formato:
            return jsonify({'error': 'Formato no encontrado'}), 404

        carpeta_formatos = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads', 'formatos')
        filename = os.path.basename(formato.archivo_url)  # Esto evita rutas raras
        return send_from_directory(carpeta_formatos, filename, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@formato_bp.route('/medida-disciplinaria/pdf', methods=['GET'])
def generar_pdf_medida_disciplinaria():
    ruta_pdf = r'C:\Users\Soporte\Documents\SistemaEvaluaciones_BACK\uploads\formatos\Medida disciplinaria.pdf'

    import os
    if not os.path.exists(ruta_pdf):
        return f"Archivo no encontrado: {ruta_pdf}", 404

    return send_file(ruta_pdf, mimetype='application/pdf')

@formato_bp.route('/medida-disciplinaria/pdf/imprimir', methods=['GET'])
def imprimir_pdf_medida_disciplinaria():
    nombre = request.args.get('nombre_empleado', None)
    num_emp = request.args.get('num_empleado', None)
    puesto = request.args.get('puesto', None)
    departamento = request.args.get('departamento', None)
    fecha = datetime.now().strftime('%d/%m/%Y')

    puestos_a_departamentos = {
        'Administrador': 'Administrativo',
        'Chef ejecutivo': 'Cocina',
        'Ama de llaves': 'Dirección',
        'AyB': 'Producción',
        'Jefe de recepcion': 'Recepción',
        'Seguridad y bienestar': 'Seguridad',
        'Director de Capital Humano': 'Capital Humano',
        'Ventas': 'Ventas',
        'Mantenimiento': 'Mantenimiento',
        # Más...
    }

    if not departamento or departamento.lower() in ['undefined', 'null', 'none', '']:
        departamento = puestos_a_departamentos.get(puesto, 'Departamento Desconocido')

    # Renderizar HTML con Jinja2
    html_out = render_template('Medida disciplinaria.html',
                               nombre_empleado=nombre,
                               num_empleado=num_emp,
                               puesto=puesto,
                               departamento=departamento,
                               fecha=fecha)

    # Convertir HTML a PDF con WeasyPrint
    pdf = HTML(string=html_out).write_pdf()

    # Crear respuesta PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    # inline para abrir en navegador, attachment para forzar descarga
    response.headers['Content-Disposition'] = 'inline; filename=medida_disciplinaria.pdf'

    return response
