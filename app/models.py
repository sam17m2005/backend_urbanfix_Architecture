from . import db

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    contrasena_hash = db.Column(db.String, nullable=False)
    telefono = db.Column(db.String(20))
    fecha_registro = db.Column(db.TIMESTAMP, server_default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'telefono': self.telefono,
            'fecha_registro': self.fecha_registro.isoformat()
        }

class Reporte(db.Model):
    __tablename__ = 'reportes'

    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.Text, nullable=False)
    codigo_folio = db.Column(db.String(50), nullable=False) 
    latitud = db.Column(db.Numeric(10, 8), nullable=False)  
    longitud = db.Column(db.Numeric(11, 8), nullable=False) 
    prioridad = db.Column(db.Integer, nullable=True)        
    fecha_creacion = db.Column(db.TIMESTAMP, server_default=db.func.now())
    
    # --- Relaciones (Claves Foráneas) ---
    usuario_creador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    funcionario_asignado_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=True) 

    def to_dict(self):
        return {
            'id': self.id,
            'descripcion': self.descripcion,
            'codigo_folio': self.codigo_folio,
            'latitud': str(self.latitud),
            'longitud': str(self.longitud),
            'prioridad': self.prioridad,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'usuario_creador_id': self.usuario_creador_id,
            'categoria_id': self.categoria_id,
            'funcionario_asignado_id': self.funcionario_asignado_id
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

class Evidencia(db.Model):
    __tablename__ = 'evidencias'

    id = db.Column(db.Integer, primary_key=True)
    url_archivo = db.Column(db.String(255), nullable=False) 
    tipo_archivo = db.Column(db.String(50), nullable=True) 
    fecha_subida = db.Column(db.TIMESTAMP, server_default=db.func.now())

    # Relaciones
    reporte_id = db.Column(db.Integer, db.ForeignKey('reportes.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'reporte_id': self.reporte_id,
            'url_archivo': self.url_archivo,
            'tipo_archivo': self.tipo_archivo,
            'fecha_subida': self.fecha_subida.isoformat() if self.fecha_subida else None
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

    # --- Relación ---
    entidad_id = db.Column(db.Integer, db.ForeignKey('entidades_publicas.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'cargo': self.cargo,
            'legajo': self.legajo,
            'entidad_id': self.entidad_id,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None
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

    #Relaciones

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'),nullable=False)
    reporte_id = db.Column(db.Integer, db.ForeignKey('reportes.id'),nullable=False)

    def to_dict(self):
        return {
            'id':self.id,
            'usuario_id': self.usuario_id,
            'reporte_id': self.reporte_id,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
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