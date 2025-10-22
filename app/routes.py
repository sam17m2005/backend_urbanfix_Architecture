from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from .models import Usuario, Reporte, Comentario, HistorialEstado, Funcionario, EstadoReporte, EntidadPublica, Zona, Apoyo, Categoria
from .utils import upload_base64_to_s3, upload_profile_pic_to_s3
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
    """
    Maneja la creación de nuevos reportes (POST) y la obtención
    de todos los reportes (GET).
    """
    
    # --- LÓGICA PARA CREAR UN NUEVO REPORTE ---
    if request.method == 'POST':
        data = request.get_json()
        
        # 1. Validar que los campos de texto requeridos existan
        required_fields = [
            'descripcion', 'direccion', 'referencia', 
            'latitud', 'longitud', 'usuario_creador_id', 
            'categoria_id', 'img_prueba_1' # img_prueba_1 es obligatoria
        ]
        
        if not all(field in data for field in required_fields):
            return jsonify({'message': 'Faltan datos obligatorios'}), 400

        # Procesar la imagen 1 (obligatoria)
        # Usamos .get() para evitar un KeyError si el campo no existe
        img_1_base64 = data.get('img_prueba_1')
        img_1_url = upload_base64_to_s3(img_1_base64)
        
        if img_1_url is None:
            # Si la imagen obligatoria falla al subirse, rechazamos la petición
            return jsonify({'message': 'Error al procesar la imagen principal (img_prueba_1)'}), 400


        img_2_base64 = data.get('img_prueba_2') # Será None si no viene
        img_2_url = upload_base64_to_s3(img_2_base64) # La función maneja None
        
        
        try:
            nuevo_reporte = Reporte(
                descripcion=data['descripcion'],
                direccion=data['direccion'],
                referencia=data['referencia'],
                
                img_prueba_1=img_1_url,  # <-- URL de S3
                img_prueba_2=img_2_url,  # <-- URL de S3 (o None)
                
                latitud=data['latitud'],
                longitud=data['longitud'],
                usuario_creador_id=data['usuario_creador_id'],
                categoria_id=data['categoria_id'],

                tipo_evento=data['tipo_evento'] #XD
            )

            # Guardar en la base de datos
            db.session.add(nuevo_reporte)
            db.session.commit()
            
            # Devolver una respuesta exitosa
            return jsonify({
                'message': 'Reporte creado exitosamente', 
                'reporte': nuevo_reporte.to_dict() # Asumo que tienes un método to_dict()
            }), 201

        except Exception as e:
            # Si algo falla al guardar en BD, hacemos rollback
            db.session.rollback()
            print(f"Error al guardar en la base de datos: {e}")
            # Idealmente, aquí deberías borrar las imágenes de S3 que 
            # ya se subieron para no dejar basura, pero es más complejo.
            return jsonify({'message': 'Error interno al guardar el reporte.'}), 500
    
    # --- LÓGICA PARA OBTENER TODOS LOS REPORTES ---
    else: # request.method == 'GET'
        try:
            reportes = Reporte.query.all()
            # Convertimos cada objeto reporte a un diccionario
            return jsonify([reporte.to_dict() for reporte in reportes]), 200
        except Exception as e:
            print(f"Error al consultar reportes: {e}")
            return jsonify({'message': 'Error al obtener los reportes.'}), 500

#Imagenes de Perfiles

@main.route('/usuarios/<int:user_id>/foto_perfil', methods=['POST'])
def update_usuario_foto(user_id):
    """
    Actualiza la foto de perfil de un Usuario.
    Espera un JSON con: { "foto_base64": "..." }
    """
    usuario = Usuario.query.get_or_404(user_id)
    data = request.get_json()

    if not data or 'foto_base64' not in data:
        return jsonify({'message': 'No se proporcionó la imagen (foto_base64)'}), 400

    img_base64 = data['foto_base64']
    
    # --- Llama a la nueva función de utils para perfiles ---
    img_url = upload_profile_pic_to_s3(img_base64)

    if img_url is None:
        return jsonify({'message': 'Error al procesar y subir la imagen de perfil'}), 500

    # --- Guarda la URL en el campo 'imagen' (como está en tu models.py) ---
    usuario.imagen = img_url 
    db.session.commit()

    return jsonify({
        'message': 'Foto de perfil actualizada exitosamente', 
        'url': img_url
    }), 200


@main.route('/funcionarios/<int:funcionario_id>/foto_perfil', methods=['POST'])
def update_funcionario_foto(funcionario_id):
    """
    Actualiza la foto de perfil de un Funcionario.
    Espera un JSON con: { "foto_base64": "..." }
    """
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    data = request.get_json()

    if not data or 'foto_base64' not in data:
        return jsonify({'message': 'No se proporcionó la imagen (foto_base64)'}), 400

    img_base64 = data['foto_base64']

    # --- Llama a la nueva función de utils para perfiles ---
    img_url = upload_profile_pic_to_s3(img_base64)

    if img_url is None:
        return jsonify({'message': 'Error al procesar y subir la imagen de perfil'}), 500

    # --- Guarda la URL en el campo 'foto_perfil_url' (que añadiste a models.py) ---
    funcionario.foto_perfil_url = img_url
    db.session.commit()

    return jsonify({
        'message': 'Foto de perfil de funcionario actualizada exitosamente', 
        'url': img_url
    }), 200

@main.route('/misreportes', methods=['GET'])
def get_mis_reportes():
    """
    Endpoint para obtener los reportes de un usuario específico.
    Recibe el ID del usuario como un query parameter.
    Ejemplo de llamada: GET /misreportes?user_id=1
    """
    # 1 Obtener el ID de usuario desde los parámetros de la URL
    user_id = request.args.get('user_id')

    # 2 Validación
    if not user_id:
        return jsonify({'error': 'El parámetro user_id es obligatorio.'}), 400
    try:
        user_id_int = int(user_id)
    except ValueError:
        return jsonify({'error': 'El user_id debe ser un número entero válido.'}), 400

    # 3 Consultar la base de datos
    try:
        reportes_del_usuario = Reporte.query.filter_by(usuario_creador_id=user_id_int).all()

        
        resultado_formateado = []
        for reporte in reportes_del_usuario:
            resultado_formateado.append({
                "id": reporte.id,
                "nombre": reporte.tipo_evento,
                "imagen_prueba_1": reporte.img_prueba_1,
                "fecha_creacion": reporte.fecha_creacion.isoformat() if reporte.fecha_creacion else None,
                "direccion": reporte.direccion,
                "estado": reporte.estado
            })

        return jsonify(resultado_formateado), 200

    except Exception as e:
        print(f"Error en /misreportes: {e}")
        return jsonify({'error': 'Ocurrió un error en el servidor.'}), 500




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