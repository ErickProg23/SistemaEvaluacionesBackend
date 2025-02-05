from datetime import datetime
from decimal import Decimal
from app import db

class Usuario(db.Model):
    __tablename__ = 'usuarios'  # Nombre de la tabla en la base de datos

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # id como clave primaria y autoincrementable
    nombre = db.Column(db.String(255), nullable=False)  # Nombre del usuario
    correo = db.Column(db.String(255), unique=True, nullable=False)  # Correo único
    contrasena = db.Column(db.String(50), nullable=False)  # Contraseña encriptada
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)  # Clave foránea a la tabla "roles"
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)  # Fecha de creación, por defecto la hora actual

    # Relación con la tabla Rol
    rol = db.relationship('Rol', backref=db.backref('usuarios', lazy=True))

    def __repr__(self):
        return f"<Nombre {self.nombre}, Correo {self.correo}, Rol {self.rol_id}>"
    

class Rol(db.Model):
    __tablename__='rol'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.String(255))

    def __repr__(self):
        return f"<Rol {self.nombre}>"
    

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
    encargados = db.relationship('Encargado', secondary='empleado_encargado', backref='empleados_rel', lazy='dynamic')
    rol = db.relationship('Rol' , backref='empleados')

    def __repr__(self):
        return f"<Nombre {self.nombre}, Puesto{self.puesto}, Activo{self.activo}, Evaluador {self.evaluador_id}, Rol {self.rol_id}>"
    

class Encargado(db.Model):
    __tablename__='encargado'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255), nullable=False)
    evaluador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    puesto = db.Column(db.String(255), nullable=False)
    num_empleado = db.Column(db.Integer, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)

    evaluador = db.relationship('Usuario', backref='encargado_usuario', backref='usuarios')
    empleados = db.relationship('Empleado', secondary='empleado_encargado', backref='encargados_rel', lazy=True)

    def __repr__(self):
        return f"<ID {self.id}, Nombre {self.nombre}, Evaluador{self.evaluador_id}, Activo{self.activo},Rol {self.rol_id}, Puesto {self.puesto}, Num. Empleado {self.num_empleado}>"

class EmpleadoEncargado(db.Model):
    __tablename__='empleado_encargado'

    empleado_id = db.Column(db.Integer, db.ForeignKey('empleado.id'), primary_key=True)
    encargado_id = db.Column(db.Integer, db.ForeignKey('encargado.id'), primary_key=True)

    def __repr__(self):
        return f"<Empleado {self.empleado_id}, Encargado {self.encargado_id}>"
    
class EncargadoUsuario(db.Model):
    __tablename__='encargado_usuario'

    encargado_id = db.Column(db.Integer, db.ForeignKey('encargado.id'), primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)

    def __repr__(self):
        return f"<Encargado {self.encargado_id}, Usuario {self.usuario_id}>"

class Pregunta(db.Model):
    __tablename__='pregunta'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    texto = db.Column(db.String(500), nullable=False)
    peso = db.Column(db.Numeric(5, 2), nullable=False)  # Usamos db.Numeric para manejar valores decimales


    def __repr__(self):
        return f"<Texto {self.texto}, Peso {self.peso}>"

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
    porcentaje = db.Column(db.Numeric(5,2), nullable=False)
    comentarios = db.Column(db.String(255), nullable=False)
    
    def __repr__(self):
        return f'<Evaluacion ID: {self.id}, Empleado ID: {self.empleado_id}, Encargado ID: {self.encargado_id}, Total Puntos: {self.total_puntos}, Porcentaje: {self.porcentaje}>'