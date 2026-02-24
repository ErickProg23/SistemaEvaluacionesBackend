from datetime import datetime
from decimal import Decimal
from app import db
from sqlalchemy.dialects.mysql import JSON

class Usuario(db.Model):
    __tablename__ = 'usuarios'  # Nombre de la tabla en la base de datos

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # id como clave primaria y autoincrementable
    nombre = db.Column(db.String(255),unique=True, nullable=False)  # Nombre del usuario
    usuario = db.Column(db.String(255), unique=True, nullable=False)  # Usuario unico
    correo = db.Column(db.String(255), unique=True, nullable=True)  # Correo electrónico
    contrasena = db.Column(db.String(50), nullable=False)  # Contraseña encriptada
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)  # Clave foránea a la tabla "roles"
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)  # Fecha de creación, por defecto la hora actual
    activo = db.Column(db.Boolean, default=True)

    # Relación con la tabla Rol
    rol = db.relationship('Rol', backref=db.backref('usuarios', lazy=True))

    def __repr__(self):
        return f"<Nombre {self.nombre}, Usuario {self.usuario}, Rol {self.rol_id}, Activo{self.activo}>"
    

class Rol(db.Model):
    __tablename__='rol'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.String(255))

    def __repr__(self):
        return f"<Rol {self.nombre}>"
    

class EmpleadoEncargado(db.Model):
    __tablename__='empleado_encargado'

    empleado_id = db.Column(db.Integer, db.ForeignKey('empleado.id'), primary_key=True)
    encargado_id = db.Column(db.Integer, db.ForeignKey('encargado.id'), primary_key=True)

    def __repr__(self):
        return f"<Empleado {self.empleado_id}, Encargado {self.encargado_id}>"

class Empleado(db.Model):
    __tablename__='empleado'


    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255), nullable=False)
    puesto = db.Column(db.String(255), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False, index=True) 
    num_empleado = db.Column(db.Integer, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    tipo_evaluacion = db.Column(db.Integer, nullable=False)

     # Relación con el modelo Encargado
    # Update this relationship
    encargados = db.relationship(
        'Encargado',
        secondary='empleado_encargado',
        back_populates='empleados',
        lazy='dynamic'
    )

    rol = db.relationship('Rol' , backref='empleados')

    def __repr__(self):
        return f"<Nombre {self.nombre}, Puesto{self.puesto}, Activo{self.activo}, Evaluadores {self.encargados}, Rol {self.rol_id}, Tipo_Evaluacion {self.tipo_evaluacion}>"
    

class Encargado(db.Model):
    __tablename__='encargado'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255), nullable=False)
    puesto = db.Column(db.String(255), nullable=False)
    num_empleado = db.Column(db.Integer, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    tipo_evaluacion = db.Column(db.Integer, nullable=False)

    usuarios = db.relationship('Usuario', secondary='encargado_usuario', backref='encargados_relacionados')
    empleados = db.relationship(
        'Empleado',
        secondary='empleado_encargado',
        back_populates='encargados',
        lazy=True,
        overlaps="empleados_rel,encargados"
    )

    def __repr__(self):
        return f"<ID {self.id}, Nombre {self.nombre}, Evaluador{self.evaluador_id}, Activo{self.activo},Rol {self.rol_id}, Puesto {self.puesto}, Num. Empleado {self.num_empleado}, Tipo evaluacion {self.tipo_evaluacion}>"
    
class EncargadoUsuario(db.Model):
    __tablename__='encargado_usuario'

    encargado_id = db.Column(db.Integer, db.ForeignKey('encargado.id'), primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)

    def __repr__(self):
        return f"<Encargado {self.encargado_id}, Usuario {self.usuario_id}>"

class Pregunta(db.Model):
    __tablename__ = 'aspecto'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    texto = db.Column(db.String(500), nullable=False)
    peso = db.Column(db.Numeric(5, 2), nullable=False)  # Manejo de decimales
    descripcion = db.Column(db.String(65535))
    tipo = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "texto": self.texto,
            "peso": float(self.peso),  # Convertir a float
            "descripcion": self.descripcion,
            "tipo": self.tipo,
            "estado": self.estado
        }

    def __repr__(self):
        return f"<Texto {self.texto}, Peso {self.peso}, Descripcion {self.descripcion}, Tipo {self.tipo}, Estado {self.estado}>"


class Respuesta(db.Model):
    __tablename__='respuesta'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    evaluacion_id = db.Column(db.Integer, db.ForeignKey('evaluacion.id') , nullable=False)
    pregunta_id = db.Column(db.Integer, db.ForeignKey('pregunta.id'), nullable=False)
    respuesta = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Evaluacion_ID {self.evaluacion_id}, Pregunta_ID {self.pregunta_id}, Respuesta{self.respuesta}>"

class Evaluacion(db.Model):
    __tablename__='evaluacion'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    empleado_id = db.Column(db.Integer, db.ForeignKey('empleado.id'), nullable=False)
    encargado_id = db.Column(db.Integer, db.ForeignKey('encargado.id'), nullable=False)
    fecha_evaluacion = db.Column(db.Date, nullable=False)
    total_puntos = db.Column(db.Numeric(5,2), nullable=False)
    porcentaje_total = db.Column(db.Numeric(5,2), nullable=False)
    comentarios = db.Column(db.String(255), nullable=False)
    aspecto = db.Column(db.String(255), nullable=False)
    ausente = db.Column(db.Boolean, default=True)
    a_tiempo = db.Column(db.Boolean, default=True)
    tipo_evaluacion = db.Column(db.Integer, nullable=False)
    num_semana = db.Column(db.Integer, nullable=False, default=0)
    periodo_anio = db.Column(db.Integer, nullable=False)
    periodo_mes = db.Column(db.Integer, nullable=True)
    
    def __repr__(self):
        return f'<Evaluacion ID: {self.id}, Empleado ID: {self.empleado_id}, Encargado ID: {self.encargado_id}, Total Puntos: {self.total_puntos}, Porcentaje: {self.porcentaje_total}, aTiempo: {self.a_tiempo}, TipSemana: {self.tipo_evaluacion},NumSemana: {self.num_semana}, Anio: {self.periodo_anio}, Mes: {self.periodo_mes}>'

class Evaluacion_Encargado(db.Model):
    __tablename__='evaluacion_encargado'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    encargado_id = db.Column(db.Integer, db.ForeignKey('encargado.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha_evaluacion = db.Column(db.Date, nullable=False)
    total_puntos = db.Column(db.Numeric(5,2), nullable=False)
    porcentaje_total = db.Column(db.Numeric(5,2), nullable=False)
    comentarios = db.Column(db.String(255), nullable=False)
    aspecto = db.Column(db.String(255), nullable=False)
    ausente = db.Column(db.Boolean, default=True)
    a_tiempo = db.Column(db.Boolean, default=True)
    num_semana = db.Column(db.Integer, nullable=False)
    tipo_evaluacion = db.Column(db.Integer, nullable=False)
    periodo_anio = db.Column(db.Integer, nullable=False)
    periodo_mes = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<Evaluacion ID: {self.id}, Encargado ID: {self.encargado_id},Usuario ID: {self.usuario_id}, Total Puntos: {self.total_puntos}, Porcentaje: {self.porcentaje_total}, aTiempo: {self.a_tiempo}, numSem: {self.num_semana}, TipSemana: {self.tipo_evaluacion}, Anio: {self.periodo_anio}, Mes: {self.periodo_mes}>'

class Notificacion(db.Model):
    __tablename__ = 'notificaciones'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_encargado = db.Column(db.Integer, db.ForeignKey('encargado.id'), nullable=False)
    id_empleado = db.Column(db.Integer, db.ForeignKey('empleado.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    accion = db.Column(db.Integer, nullable=False)
    activo = db.Column(db.Boolean, default=True)

    # Relaciones
    encargado = db.relationship('Encargado', backref='notificaciones')
    empleado = db.relationship('Empleado', backref='notificaciones')

    def __repr__(self):
        return f'<Notificacion ID: {self.id}, Encargado ID: {self.id}, Empleado ID: {self.id}, Accion: {self.accion}, Fecha: {self.fecha}, Activo: {self.activo}>'

class Formato(db.Model):
    __tablename__ = 'formatos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    archivo_url = db.Column(db.String(500), nullable=False)
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Formato ID: {self.id}, Nombre: {self.nombre}, URL: {self.archivo_url}>'


class EvaluacionTemporal(db.Model):
    __tablename__ = 'evaluaciones_temporales'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_encargado = db.Column(
        db.Integer,
        db.ForeignKey('encargado.id'),
        nullable=False
    )

    periodo_anio = db.Column(db.Integer, nullable=False)
    periodo_mes = db.Column(db.Integer, nullable=False)

    dato = db.Column(db.JSON, nullable=False)

    fecha_guardado = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )

    __table_args__ = (
        db.UniqueConstraint(
            'id_encargado',
            'periodo_anio',
            'periodo_mes',
            name='uq_encargado_periodo'
        ),
    )

    def __repr__(self):
        return (
            f'<EvaluacionTemporal Encargado:{self.id_encargado} '
            f'Periodo:{self.periodo_mes}/{self.periodo_anio}>'
        )
    
class EvaluacionAtrasada(db.Model):
    __tablename__ = 'evaluaciones_atrasadas'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_encargado = db.Column(db.Integer, db.ForeignKey('encargado.id'), nullable=False)
    num_semana = db.Column(db.Integer, nullable=False)
    periodo_mes = db.Column(db.Integer, nullable=False)
    periodo_anio = db.Column(db.Integer, nullable=False)
    fecha_detectado = db.Column(db.Date, default=datetime.utcnow)
    notificado = db.Column(db.Boolean, default=False)
    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<EvaluacionAtrasada ID: {self.id}, Encargado ID: {self.id_encargado}, Semana: {self.num_semana}, Periodo: {self.periodo_mes}/{self.periodo_anio}, Fecha Detectado: {self.fecha_detectado}>'

class Ticket(db.Model):
    __tablename__ = 'ticket'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    titulo = db.Column(db.String(45), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    departamento = db.Column(db.String(255), nullable=False)
    area = db.Column(db.String(255), nullable=False)
    categoria = db.Column(db.String(255), nullable=False)
    estado = db.Column(db.String(45), nullable=False, default='Abierto')  # Estado del ticket, por defecto 'Abierto'
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_cierre = db.Column(db.DateTime)
    asignado_a = db.Column(db.Integer, db.ForeignKey('empleado.id'), nullable=True)  # ID del empleado asignado, si aplica

    usuario_rel = db.relationship('Usuario', foreign_keys=[usuario_id], backref='tickets_creados')
    empleado_rel = db.relationship('Empleado', foreign_keys=[asignado_a], backref='tickets_asignados')


    def __repr__(self):
        return f'<Ticket ID: {self.id}, Titulo: {self.titulo}, Estado: {self.estado}, Usuario ID: {self.usuario_id}, Asignado A: {self.asignado_a}>'

class Configuracion(db.Model):
    __tablename__ = 'configuraciones'

    clave = db.Column(db.String(50), primary_key=True)
    valor = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Configuracion {self.clave}: {self.valor}>'

class TarifaHabitacion(db.Model):
    __tablename__ = 'tarifas_habitaciones'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio_mxn = db.Column(db.Numeric(10, 2), nullable=False)
    orden = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<TarifaHabitacion {self.nombre}: {self.precio_mxn}>'

class MensajeTicket(db.Model):
    __tablename__ = 'mensajes_ticket'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.now)

    # Relaciones (para poder acceder al nombre del usuario fácilmente)
    usuario_rel = db.relationship('Usuario', backref='mensajes_enviados')
    ticket_rel = db.relationship('Ticket', backref='mensajes')

    def __repr__(self):
        return f'<MensajeTicket ID: {self.id}, Ticket ID: {self.ticket_id}, Usuario ID: {self.usuario_id}, Mensaje: {self.mensaje}, Fecha: {self.fecha}>'
    
class NotificacionTicket(db.Model):
    __tablename__ = 'notificaciones_tickets'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    cantidad_mensajes = db.Column(db.Integer, default=1)
    ultimo_mensaje = db.Column(db.String(255)) # Limitamos longitud para preview
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    leido = db.Column(db.Boolean, default=False)

    # Relaciones
    usuario_rel = db.relationship('Usuario', backref=db.backref('notificaciones_tickets', lazy=True))
    ticket_rel = db.relationship('Ticket', backref=db.backref('notificaciones_usuarios', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'ticket_id': self.ticket_id,
            'ticket_titulo': self.ticket_rel.titulo if self.ticket_rel else 'Ticket',
            'cantidad_mensajes': self.cantidad_mensajes,
            'ultimo_mensaje': self.ultimo_mensaje,
            'fecha': self.fecha_actualizacion.isoformat(),
            'leido': self.leido,
            'tipo': 'ticket_chat' # Útil para distinguir en el frontend
        }