from flask import Blueprint, request, jsonify
from .models import Usuario, Reporte, Comentario, Evidencia, HistorialEstado, Funcionario, EstadoReporte, EntidadPublica, Zona, Apoyo, Categoria
from . import db

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
            contrasena_hash=data['contrasena'],
            telefono=data.get('telefono')
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        return jsonify({'message': 'Usuario creado exitosamente', 'usuario': nuevo_usuario.to_dict()}), 201
    else:
        usuarios = Usuario.query.all()
        return jsonify([usuario.to_dict() for usuario in usuarios])

@main.route('/usuarios/<int:user_id>', methods=['GET'])
def get_usuario(user_id):
    usuario = Usuario.query.get_or_404(user_id)
    return jsonify(usuario.to_dict())


@main.route('/reportes', methods=['GET', 'POST'])
def handle_reportes():
    if request.method == 'POST':
        data = request.get_json()
        
        required_fields = ['descripcion', 'latitud', 'longitud', 'usuario_creador_id', 'categoria_id', 'codigo_folio']
        
        if not all(field in data for field in required_fields):
            return jsonify({'message': 'Faltan datos obligatorios'}), 400

        nuevo_reporte = Reporte(
            descripcion=data['descripcion'],
            latitud=data['latitud'],
            longitud=data['longitud'],
            usuario_creador_id=data['usuario_creador_id'],
            categoria_id=data['categoria_id'],
            codigo_folio=data['codigo_folio'],
            prioridad=data.get('prioridad'),
            funcionario_asignado_id=data.get('funcionario_asignado_id')
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
