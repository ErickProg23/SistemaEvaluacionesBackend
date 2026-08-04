# SistemaEvaluacionesBackend

Backend API para la gestión de evaluaciones de personal, encargados, preguntas, notificaciones, tickets, formatos y módulos auxiliares del sistema. Está construido con Flask, usa SQLAlchemy como ORM y expone endpoints REST consumidos por un frontend externo.

## Tecnologías principales
- Python 3
- Flask
- Flask-SQLAlchemy
- Flask-JWT-Extended
- Flask-Bcrypt
- Flask-CORS
- Flask-Mail
- MySQL con `PyMySQL`
- Utilidades de exportación y documentos: `pandas`, `openpyxl`, `reportlab`, `weasyprint`, `PyPDF2`, `PyMuPDF`

## Arquitectura general
- `run.py`: punto de entrada para levantar la aplicación en desarrollo.
- `app/__init__.py`: factory `create_app()`, inicializa extensiones y registra blueprints.
- `app/config.py`: carga variables de entorno desde `.env` y construye la configuración principal.
- `app/models.py`: define el modelo de datos completo del sistema.
- `app/routes/`: concentra los módulos REST por dominio.
- `app/services/`: lógica auxiliar reutilizable, por ejemplo correo y detección de evaluaciones atrasadas.
- `app/templates/`: plantillas HTML usadas para formatos/documentos.
- `uploads/`: archivos subidos o publicados por el sistema.
- `instance/`: almacenamiento local auxiliar; aunque existe `evaluaciones.db`, la configuración activa apunta a MySQL.

## Cómo levantar el proyecto
1. Crear y activar un entorno virtual.
2. Instalar dependencias con `pip install -r requirements.txt`.
3. Crear un archivo `.env` con la configuración necesaria.
4. Asegurar que la base de datos MySQL exista y sea accesible.
5. Ejecutar `python run.py`.

Comando típico en Windows:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Variables de entorno
El proyecto usa estas variables desde `.env`:
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_NAME`
- `JWT_SECRET_KEY`
- `MAIL_SERVER`
- `MAIL_PORT`
- `MAIL_USE_SSL`
- `MAIL_USE_TLS`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_DEFAULT_SENDER`
- `EVALS_LAST_FRIDAY_OVERRIDE`: override opcional para probar la lógica de evaluaciones atrasadas.

Ejemplo base:

```env
DB_USER=usuario
DB_PASSWORD=secreto
DB_HOST=localhost
DB_NAME=sistema_evaluaciones
JWT_SECRET_KEY=clave_jwt
MAIL_SERVER=smtp.midominio.com
MAIL_PORT=465
MAIL_USE_SSL=True
MAIL_USE_TLS=False
MAIL_USERNAME=correo@midominio.com
MAIL_PASSWORD=secreto
MAIL_DEFAULT_SENDER=correo@midominio.com
```

## Modelos principales
- `Usuario`, `Rol`: autenticación, autorización y catálogo de roles.
- `Empleado`, `Encargado`, `EmpleadoEncargado`, `EncargadoUsuario`: personal y relaciones operativas.
- `Pregunta`, `Respuesta`: catálogo de aspectos y detalle de respuestas.
- `Evaluacion`, `Evaluacion_Encargado`: evaluaciones a empleados y evaluaciones de encargado.
- `EvaluacionTemporal`: guardado temporal por período.
- `EvaluacionAtrasada`: control de evaluaciones no realizadas; incluye restricción única por encargado y período.
- `Notificacion`: avisos relacionados con evaluaciones.
- `Formato`: catálogo de formatos y archivos disponibles.
- `Ticket`, `MensajeTicket`, `NotificacionTicket`: mesa de ayuda y chat asociado.
- `Configuracion`, `TarifaHabitacion`, `HabitacionesInspecciones`: módulos auxiliares del sistema.

## Módulos de rutas
- `usuarios_routes.py`: CRUD parcial y activación/desactivación de usuarios.
- `login_routes.py`: autenticación.
- `obtencionDatos_routes.py`: consultas de empleados, encargados y relaciones.
- `creacion_routes.py` y `actualizacionDatos_routes.py`: altas y edición de empleados/encargados.
- `preguntas_routes.py`: catálogo de preguntas/aspectos de evaluación.
- `evaluaciones_routes.py`: creación de evaluaciones, consulta histórica, exportación CSV, temporales y flujo de evaluaciones atrasadas.
- `promedio_routes.py`: reportes agregados, promedios y exportes por período/encargado.
- `notificaciones_routes.py`: notificaciones, lectura y limpieza.
- `ticket_routes.py`: creación, consulta, asignación, estados y mensajería de tickets.
- `formato_routes.py` y `uploads_routes.py`: descarga/impresión de formatos y exposición de archivos.
- `roles_routes.py`, `tarifas_routes.py`, `configuracion_routes.py`: catálogos administrativos.
- `habitacionesInspecciones_routes.py`: módulo de inspección de habitaciones.
- `main_routes.py`: endpoints generales y utilitarios adicionales bajo `/api`.

## Prefijos base de la API
Los blueprints se registran con estos prefijos:
- `/api/users`
- `/api/login`
- `/api/datos`
- `/api/preguntas`
- `/api/actualizacion`
- `/api/creacion`
- `/api/evaluacion`
- `/api/notificaciones`
- `/api/formatos`
- `/api/promedio`
- `/api/tickets`
- `/api/retroalimentacion`
- `/api/roles`
- `/api/tarifas`
- `/api/configuracion`
- `/api`
- `/uploads`
- `/api/habitacionesInspecciones`

## Lógica relevante del dominio
- Las evaluaciones manejan `periodo_mes`, `periodo_anio`, `num_semana`, `tipo_evaluacion`, `ausente` y `a_tiempo`.
- El sistema soporta guardado temporal de evaluaciones por encargado y período.
- La detección de evaluaciones atrasadas usa la regla del último viernes del mes y hoy puede sincronizar registros antes de consultarlos.
- Existen servicios para notificar por correo a encargados con atrasos.

## Consideraciones actuales
- `run.py` ejecuta Flask en modo `debug=True`; conviene ajustar esto para producción.
- El proyecto tiene dependencias amplias; varias son de generación de reportes/documentos y no todas participan en cada flujo.
- Existe soporte para correo, JWT, CORS y exportaciones, pero el despliegue depende de la correcta configuración del `.env` y de MySQL.
