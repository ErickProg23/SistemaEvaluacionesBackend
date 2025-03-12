from datetime import datetime
from decimal import Decimal
from app import db

class Usuario(db.Model):
    __tablename__ = 'usuarios'  # Nombre de la tabla en la base de datos

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # id como clave primaria y autoincrementable
    nombre = db.Column(db.String(255),unique=True, nullable=False)  # Nombre del usuario
    correo = db.Column(db.String(255), unique=True, nullable=False)  # Correo único
    contrasena = db.Column(db.String(50), nullable=False)  # Contraseña encriptada
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)  # Clave foránea a la tabla "roles"
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)  # Fecha de creación, por defecto la hora actual
    activo = db.Column(db.Boolean, default=True)

    # Relación con la tabla Rol
    rol = db.relationship('Rol', backref=db.backref('usuarios', lazy=True))

    def __repr__(self):
        return f"<Nombre {self.nombre}, Correo {self.correo}, Rol {self.rol_id}, Activo{self.activo}>"
    

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
        return f"<Nombre {self.nombre}, Puesto{self.puesto}, Activo{self.activo}, Evaluadores {self.encargados}, Rol {self.rol_id}>"
    

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

    encargados = db.relationship('Usuario', secondary='encargado_usuario', backref='usuarios_rel')
    empleados = db.relationship(
        'Empleado',
        secondary='empleado_encargado',
        back_populates='encargados',
        lazy=True,
        overlaps="empleados_rel,encargados"
    )

    def __repr__(self):
        return f"<ID {self.id}, Nombre {self.nombre}, Evaluador{self.evaluador_id}, Activo{self.activo},Rol {self.rol_id}, Puesto {self.puesto}, Num. Empleado {self.num_empleado}>"
    
class EncargadoUsuario(db.Model):
    __tablename__='encargado_usuario'

    encargado_id = db.Column(db.Integer, db.ForeignKey('encargado.id'), primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)

    def __repr__(self):
        return f"<Encargado {self.encargado_id}, Usuario {self.usuario_id}>"

class Pregunta(db.Model):
    __tablename__ = 'pregunta'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    texto = db.Column(db.String(500), nullable=False)
    peso = db.Column(db.Numeric(5, 2), nullable=False)  # Manejo de decimales
    descripcion = db.Column(db.String(65535))

    def to_dict(self):
        return {
            "id": self.id,
            "texto": self.texto,
            "descripcion": self.descripcion
        }

    def __repr__(self):
        return f"<Texto {self.texto}, Peso {self.peso}, Descripcion {self.descripcion}>"


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
    
    def __repr__(self):
        return f'<Evaluacion ID: {self.id}, Empleado ID: {self.empleado_id}, Encargado ID: {self.encargado_id}, Total Puntos: {self.total_puntos}, Porcentaje: {self.porcentaje}>'

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