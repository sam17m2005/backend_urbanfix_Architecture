from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from .models import Usuario, Reporte, Comentario, Evidencia, HistorialEstado, Funcionario, EstadoReporte, EntidadPublica, Zona, Apoyo, Categoria
from . import db
from werkzeug.security import generate_password_hash, check_password_hash


main = Blueprint('main', __name__)

@main.route('/')
def index():
    return "¡La aplicación estructurada está funcionando!"

@main.route('/usuarios', methods=['GET', 'POST'])
def handle_usuarios():
    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('nombre') or not data.get('email') or not data.get('contrasena'):
            return jsonify({'message': 'Faltan datos'}), 400

        nuevo_usuario = Usuario(
            nombre=data['nombre'],
            email=data['email'],
            contrasena_hash=generate_password_hash(data['contrasena']),
            telefono=data.get('telefono')
        )
        try: 
            db.session.add(nuevo_usuario)
            db.session.commit()
            return jsonify({'message': 'Usuario creado exitosamente', 'usuario': nuevo_usuario.to_dict()}), 201
        except IntegrityError:
            db.session.rollback() 
            return jsonify({'message': 'Ya existe una cuenta con este correo electrónico.'}), 409
    else:
        usuarios = Usuario.query.all()
        return jsonify([usuario.to_dict() for usuario in usuarios])
    
#Endpoint Inicio de sesion
@main.route('/login',methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('contrasena'):
        return jsonify({'message': 'Faltan email o contraseña'}), 400
    
    email = data['email']
    contrasena = data['contrasena']
    
    user = Usuario.query.filter_by(email=email).first()
    funcionario = Funcionario.query.filter_by(email=email).first()

    if not user and not funcionario:
        return jsonify({'message': 'La cuenta no existe. Por favor, regístrate.'}), 404

    if user:
        if user.check_password(contrasena):
            return jsonify({
                'message': 'Inicio de sesión exitoso',
                'role': 'usuario',
                'user_data': user.to_dict()
            }), 200
        else:
            return jsonify({'message': 'Credenciales incorrectas'}), 401

    if funcionario:
        if funcionario.check_password(contrasena):
            return jsonify({
                'message': 'Inicio de sesión exitoso',
                'role': 'funcionario',
                'user_data': funcionario.to_dict()
            }), 200
        else:
            return jsonify({'message': 'Credenciales incorrectas'}), 401


@main.route('/usuarios/<int:user_id>', methods=['GET'])
def get_usuario(user_id):
    usuario = Usuario.query.get_or_404(user_id)
    return jsonify(usuario.to_dict())


@main.route('/reportes', methods=['GET', 'POST'])
def handle_reportes():
    if request.method == 'POST':
        data = request.get_json()
        
        required_fields = ['descripcion','direccion','referencia','latitud', 'longitud', 'usuario_creador_id', 'categoria_id', 'img_prueba_1']
        
        if not all(field in data for field in required_fields):
            return jsonify({'message': 'Faltan datos obligatorios'}), 400

        nuevo_reporte = Reporte(
            descripcion=data['descripcion'],
            direccion=data['direccion'],
            referencia=data['referencia'],
            img_prueba_1=data['https://urbanfiximagenesreportes.s3.us-east-1.amazonaws.com/nombre de la imagen'], #TODO
            img_prueba_2=data['si o que. mirar como handelear'], #TODO
            latitud=data['latitud'],
            longitud=data['longitud'],
            usuario_creador_id=data['usuario_creador_id'],
            categoria_id=data['categoria_id']
        )

        db.session.add(nuevo_reporte)
        db.session.commit()
        
        return jsonify({'message': 'Reporte creado exitosamente', 'reporte': nuevo_reporte.to_dict()}), 201
    
    else:
        reportes = Reporte.query.all()
        return jsonify([reporte.to_dict() for reporte in reportes])

@main.route('/categorias', methods=['GET'])
def get_categorias():
    """Devuelve una lista de todas las categorías."""
    try:
        categorias = Categoria.query.all()
        return jsonify([categoria.to_dict() for categoria in categorias]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/estados-reporte', methods=['GET'])
def get_estados_reporte():
    """Devuelve una lista de todos los posibles estados de un reporte."""
    try:
        estados = EstadoReporte.query.all()
        return jsonify([estado.to_dict() for estado in estados]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/reportes/<int:reporte_id>/comentarios', methods=['POST'])
def crear_comentario(reporte_id):
    """Crea un nuevo comentario para un reporte específico."""
    data = request.get_json()
    
    if not all(key in data for key in ['texto', 'usuario_id']):
        return jsonify({'message': 'Faltan los campos "texto" y "usuario_id"'}), 400

    reporte = Reporte.query.get(reporte_id)
    if not reporte:
        return jsonify({'message': 'El reporte con el id especificado no existe'}), 404

    nuevo_comentario = Comentario(
        texto=data['texto'],
        usuario_id=data['usuario_id'],
        reporte_id=reporte_id 
    )

    db.session.add(nuevo_comentario)
    db.session.commit()

    return jsonify({'message': 'Comentario creado exitosamente', 'comentario': nuevo_comentario.to_dict()}), 201

#Endpoint para Entidades
@main.route('/entidades', methods=['GET', 'POST'])
def handle_entidades():
    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('nombre'):
            return jsonify({'message': 'El campo "nombre" es obligatorio'}), 400
        
        nueva_entidad = EntidadPublica(nombre=data['nombre'])
        db.session.add(nueva_entidad)
        db.session.commit()

        return jsonify({
            'message': 'Entidad pública creada exitosamente',
            'entidad': nueva_entidad.to_dict()
        }), 200
    
    else:
        entidades = EntidadPublica.query.all()
        return jsonify([entidad.to_dict() for entidad in entidades])


#Endpoint para Funcionarios
@main.route('/funcionarios', methods=['POST'])
def crear_funcionario():
    data = request.get_json()

    required_fields = ['nombre', 'email', 'contrasena', 'entidad_id']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Faltan datos obligatorios'}), 400
    
    nuevo_funcionario = Funcionario(
        nombre=data['nombre'],
        email=data['email'],
        contrasena_hash=generate_password_hash(data['contrasena']),
        entidad_id=data['entidad_id'],
        cargo=data.get('cargo'),
        legajo=data.get('legajo')
    )

    try: 
        db.session.add(nuevo_funcionario)
        db.session.commit()
        return jsonify({'message': 'Funcionario creado exitosamente', 'usuario': nuevo_funcionario.to_dict()}), 201
    except IntegrityError:
        db.session.rollback() 
        return jsonify({'message': 'Ya existe una cuenta con este correo electrónico.'}), 409
    
@main.route('/funcionarios', methods=['GET'])
def get_funcionarios():
    try:
        funcionarios = Funcionario.query.all()
        return jsonify([f.to_dict() for f in funcionarios]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
#Endpoints ACTUALIZACION de usuarios(Pendiente para que funcione porque me metio el dih XD)
@main.route('/usuarios/<int:user_id>', methods=['PUT'])
def update_usuario(user_id):
    usuario = Usuario.query.get_or_404(user_id)
    data = request.get_json()

    if not data:
        return jsonify({'message': 'No se recibieron datos'}), 400

    if 'nombre' in data:
        usuario.nombre = data['nombre']

    if 'contrasena' in data and data['contrasena']:
        usuario.contrasena_hash = generate_password_hash(data['contrasena'])

    db.session.commit()
    return jsonify({'message': 'Perfil de usuario actualizado exitosamente', 'usuario': usuario.to_dict()}), 200


@main.route('/funcionarios/<int:funcionario_id>', methods=['PUT'])
def update_funcionario(funcionario_id):
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    data = request.get_json()

    if not data:
        return jsonify({'message': 'No se recibieron datos'}), 400

    if 'nombre' in data:
        funcionario.nombre = data['nombre']

    if 'contrasena' in data and data['contrasena']:
        funcionario.contrasena_hash = generate_password_hash(data['contrasena'])

    db.session.commit()
    return jsonify({'message': 'Perfil de funcionario actualizado exitosamente', 'funcionario': funcionario.to_dict()}), 200


#Endpint para eliminar cuenta
@main.route('/usuarios/<int:user_id>', methods=['DELETE'])
def delete_usuario(user_id):
    usuario = Usuario.query.get_or_404(user_id)
    db.session.delete(usuario)
    db.session.commit()
    return jsonify({'message': 'Usuario eliminado exitosamente'}), 200


@main.route('/funcionarios/<int:funcionario_id>', methods=['DELETE'])
def delete_funcionario(funcionario_id):
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    db.session.delete(funcionario)
    db.session.commit()
    return jsonify({'message': 'Funcionario eliminado exitosamente'}), 200