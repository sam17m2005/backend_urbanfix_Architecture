from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False) # Mk yo creo que el inicio de sesión solo sea por emaiL
    contrasena_hash = db.Column(db.String, nullable=False)
    telefono = db.Column(db.String(20))
    fecha_registro = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    imagen = db.Column(db.String(200), unique=True, nullable=False)

    def __init__(self, **kwargs):
        super(Usuario, self).__init__(**kwargs)
        if self.fecha_registro is None:
            self.fecha_registro = datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'telefono': self.telefono,
            'fecha_registro': self.fecha_registro.isoformat(),
            'imagen': self.imagen
        }
    
    #Seteamos la contraseña bastante a la fuerza entonces no creamos metodo para crear contraseña, pero si para checkear

    def check_password(self, contrasena):
        return check_password_hash(self.contrasena_hash, contrasena)

class Reporte(db.Model):
    __tablename__ = 'reportes'

    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.Text, nullable=False)
    direccion = db.Column(db.String(100), nullable=False)
    referencia = db.Column(db.String(100), nullable=False) 
    latitud = db.Column(db.Numeric(10, 8), nullable=False)  
    longitud = db.Column(db.Numeric(11, 8), nullable=False)
    fecha_creacion = db.Column(db.TIMESTAMP, server_default=db.func.now())
    tipo_evento = db.Column(db.String(200), nullable=False) #XD como los odio amigos
    img_prueba_1 = db.Column(db.String(200), unique=True, nullable=False) #Imagen 1
    img_prueba_2 = db.Column(db.String(200)) #Imagen 2
    estado = db.Column(db.String(50))

    
    # --- Relaciones (Claves Foráneas) ---
    usuario_creador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    funcionario_asignado_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=True) 

    # CÓDIGO CORREGIDO
    def to_dict(self, current_user_id=None, current_user_role=None):
        
        apoyo_count = db.session.query(func.count(Apoyo.id)).filter(
            Apoyo.reporte_id == self.id,
            Apoyo.tipo == 'like'
        ).scalar() or 0
        
        desapoyo_count = db.session.query(func.count(Apoyo.id)).filter(
            Apoyo.reporte_id == self.id,
            Apoyo.tipo == 'dislike' 
        ).scalar() or 0

        current_user_reaction = None
        if current_user_id and current_user_role:
            # Empezar la consulta
            query = db.session.query(Apoyo.tipo).filter(Apoyo.reporte_id == self.id)
            
            # Filtrar por el rol correcto
            if current_user_role == 'usuario':
                query = query.filter(Apoyo.usuario_id == current_user_id)
            elif current_user_role == 'funcionario':
                query = query.filter(Apoyo.funcionario_id == current_user_id)
            
            # Obtener el resultado
            reaction = query.scalar()
            current_user_reaction = reaction
            
     
        categoria = Categoria.query.get(self.categoria_id)
        categoria_nombre = categoria.nombre if categoria else None
        
        nombre_reporte = self.tipo_evento

        return {
            'id': self.id,
            'descripcion': self.descripcion,
            'direccion': self.direccion,
            'referencia': self.referencia,
            'img_prueba_1': self.img_prueba_1,
            'img_prueba_2': self.img_prueba_2,
            'latitud': str(self.latitud),
            'longitud': str(self.longitud),
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'usuario_creador_id': self.usuario_creador_id,
            'categoria_id': self.categoria_id,
            'funcionario_asignado_id': self.funcionario_asignado_id,
            'apoyos_count': apoyo_count,
            'desapoyos_count': desapoyo_count,
            'current_user_reaction': current_user_reaction,
            'estado': self.estado,
            'categoria_nombre': categoria_nombre,
            'nombre': nombre_reporte 
        }


class Comentario(db.Model):
    __tablename__ = 'comentarios'

    id = db.Column(db.Integer, primary_key=True)
    texto = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.TIMESTAMP, server_default=db.func.now())

    #Relaciones
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'),nullable=False)
    reporte_id = db.Column(db.Integer, db.ForeignKey('reportes.id'),nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'reporte_id': self.reporte_id,
            'usuario_id': self.usuario_id,
            'texto': self.texto,
            'fecha_creacion': self.fecha_creacion.isoformat()
        }


class HistorialEstado(db.Model):
    __tablename__ = 'historial_estados'

    id = db.Column(db.Integer, primary_key=True)
    observaciones = db.Column(db.Text, nullable=True) 
    fecha_cambio = db.Column(db.TIMESTAMP, server_default=db.func.now())

    # --- Relaciones ---
    reporte_id = db.Column(db.Integer, db.ForeignKey('reportes.id'), nullable=False)
    estado_id = db.Column(db.Integer, db.ForeignKey('estados_reporte.id'), nullable=False) 
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'reporte_id': self.reporte_id,
            'estado_id': self.estado_id,
            'funcionario_id': self.funcionario_id,
            'observaciones': self.observaciones,
            'fecha_cambio': self.fecha_cambio.isoformat() if self.fecha_cambio else None
        }

class Funcionario(db.Model):
    __tablename__ = 'funcionarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    contrasena_hash = db.Column(db.String, nullable=False)
    cargo = db.Column(db.String(100))
    legajo = db.Column(db.String(50))
    fecha_registro = db.Column(db.TIMESTAMP, server_default=db.func.now())
    foto_perfil_url = db.Column(db.String(255), nullable=True)

    # --- Relación ---
    entidad_id = db.Column(db.Integer, db.ForeignKey('entidades_publicas.id'), nullable=False)

    def __init__(self, **kwargs):
        super(Funcionario, self).__init__(**kwargs)
        if self.fecha_registro is None:
            self.fecha_registro = datetime.utcnow()

    def check_password(self, contrasena):
        return check_password_hash(self.contrasena_hash, contrasena)

    def to_dict(self):

        entidad = EntidadPublica.query.get(self.entidad_id)
        entidad_nombre = entidad.nombre if entidad else None

        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'cargo': self.cargo,
            'legajo': self.legajo,
            'entidad_id': self.entidad_id,
            'entidad_nombre': entidad_nombre,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None,
            'foto_perfil_url': self.foto_perfil_url
        }

class EstadoReporte(db.Model):
    __tablename__ = 'estados_reporte'

    id = db.Column(db.Integer, primary_key=True)
    nombre_estado = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre_estado': self.nombre_estado
        }

class EntidadPublica(db.Model):
    __tablename__ = 'entidades_publicas'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), unique=True, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre
        }

class Zona(db.Model):
    __tablename__ = 'zonas'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)

    #Relaciones
    entidad_id = db.Column(db.Integer, db.ForeignKey('entidades_publicas.id'),nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'entidad_id':self.entidad_id
        }

class Apoyo(db.Model):
    __tablename__ = 'apoyos'

    id = db.Column(db.Integer, primary_key=True)
    fecha_creacion = db.Column(db.TIMESTAMP, server_default=db.func.now())
    tipo = db.Column(db.String(10), nullable=False, default='like')

    #Relaciones

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'),nullable=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey('reportes.id'),nullable=False)

    __table_args__ = (
        db.UniqueConstraint('usuario_id', 'reporte_id', name='uq_usuario_reporte'),
        db.UniqueConstraint('funcionario_id', 'reporte_id', name='uq_funcionario_reporte')
    )

    def to_dict(self):
        return {
            'id':self.id,
            'usuario_id': self.usuario_id,
            'reporte_id': self.reporte_id,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'tipo': self.tipo
        }

class Categoria(db.Model):
    __tablename__ = 'categorias'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    descripcion = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion
        }