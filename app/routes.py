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
                estado='Nuevo',


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
            current_user_id = request.args.get('user_id', default=None, type=int)
            reportes = Reporte.query.all()
            # Convertimos cada objeto reporte a un diccionario
            return jsonify([reporte.to_dict(current_user_id=current_user_id) for reporte in reportes]), 200
        except Exception as e:
            print(f"Error al consultar reportes: {e}")
            return jsonify({'message': 'Error al obtener los reportes.'}), 500
        

#Likes y Dislikes
@main.route('/reportes/<int:reporte_id>/reaccion', methods=['POST'])
def set_reaccion(reporte_id):
    """
    Añade o actualiza la reacción (like/dislike) de un actor
    (ya sea 'usuario' o 'funcionario').
    """
    data = request.get_json()

    # ▼▼▼ CAMBIO: Espera 'actor_id' y 'role' en lugar de 'usuario_id' ▼▼▼
    if not data or 'actor_id' not in data or 'role' not in data or 'tipo' not in data:
        return jsonify({'message': 'Faltan datos (actor_id, role, tipo)'}), 400
    
    actor_id = data['actor_id']
    actor_role = data['role']
    tipo_reaccion = data['tipo'].lower()
    # ▲▲▲ FIN DE CAMBIO ▲▲▲

    if tipo_reaccion not in ['like', 'dislike']:
         return jsonify({'message': "Tipo de reacción inválido (debe ser 'like' o 'dislike')"}), 400

    # Verificar que el reporte exista
    reporte = Reporte.query.get(reporte_id)
    if not reporte: return jsonify({'message': 'Reporte no encontrado'}), 404

    # ▼▼▼ CAMBIO: Validar que el actor (usuario o funcionario) exista ▼▼▼
    actor = None
    if actor_role == 'usuario':
        actor = Usuario.query.get(actor_id)
    elif actor_role == 'funcionario':
        actor = Funcionario.query.get(actor_id)
    else:
        return jsonify({'message': "Rol inválido (debe ser 'usuario' o 'funcionario')"}), 400
    
    if not actor: return jsonify({'message': 'Actor (usuario/funcionario) no encontrado'}), 404
    # ▲▲▲ FIN DE CAMBIO ▲▲▲

    # ▼▼▼ CAMBIO: Buscar la reacción existente basado en el ROL ▼▼▼
    existing_reaccion = None
    query = Apoyo.query.filter_by(reporte_id=reporte_id)
    if actor_role == 'usuario':
        existing_reaccion = query.filter_by(usuario_id=actor_id).first()
    else: # actor_role == 'funcionario'
        existing_reaccion = query.filter_by(funcionario_id=actor_id).first()
    # ▲▲▲ FIN DE CAMBIO ▲▲▲

    try:
        if existing_reaccion:
            # Si ya existe, solo actualiza el tipo
            existing_reaccion.tipo = tipo_reaccion
            db.session.commit()
            return jsonify({'message': f'Reacción actualizada a {tipo_reaccion}'}), 200
        else:
            # ▼▼▼ CAMBIO: Crear la nueva reacción basado en el ROL ▼▼▼
            nueva_reaccion = None
            if actor_role == 'usuario':
                nueva_reaccion = Apoyo(
                    usuario_id=actor_id, 
                    reporte_id=reporte_id, 
                    tipo=tipo_reaccion
                )
            else: # actor_role == 'funcionario'
                nueva_reaccion = Apoyo(
                    funcionario_id=actor_id, 
                    reporte_id=reporte_id, 
                    tipo=tipo_reaccion
                )
            # ▲▲▲ FIN DE CAMBIO ▲▲▲
            
            db.session.add(nueva_reaccion)
            db.session.commit()
            return jsonify({'message': f'Reacción ({tipo_reaccion}) agregada'}), 201

    except IntegrityError: 
         db.session.rollback()
         return jsonify({'message': 'Error de concurrencia al reaccionar'}), 409
    except Exception as e:
        db.session.rollback()
        print(f"Error al establecer reacción: {e}")
        return jsonify({'message': 'Error interno al establecer reacción'}), 500

@main.route('/reportes/<int:reporte_id>/reaccion', methods=['DELETE'])
def remove_reaccion(reporte_id):
    data = request.get_json()

    # ▼▼▼ CAMBIO: Espera 'actor_id' y 'role' ▼▼▼
    if not data or 'actor_id' not in data or 'role' not in data:
        return jsonify({'message': 'Falta el ID del actor (actor_id) o el rol (role)'}), 400

    actor_id = data['actor_id']
    actor_role = data['role']
    # ▲▲▲ FIN DE CAMBIO ▲▲▲

    # ▼▼▼ CAMBIO: Buscar la reacción existente basado en el ROL ▼▼▼
    reaccion = None
    query = Apoyo.query.filter_by(reporte_id=reporte_id)
    if actor_role == 'usuario':
        reaccion = query.filter_by(usuario_id=actor_id).first()
    elif actor_role == 'funcionario':
        reaccion = query.filter_by(funcionario_id=actor_id).first()
    else:
        return jsonify({'message': "Rol inválido"}), 400
    # ▲▲▲ FIN DE CAMBIO ▲▲▲

    if not reaccion: return jsonify({'message': 'El actor no ha reaccionado a este reporte'}), 404

    try:
        db.session.delete(reaccion)
        db.session.commit()
        return jsonify({'message': 'Reacción eliminada exitosamente'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar reacción: {e}")
        return jsonify({'message': 'Error interno al eliminar reacción'}), 500

# --- RUTAS DE LISTAS DE USUARIO ---

@main.route('/usuarios/<int:user_id>/apoyos', methods=['GET'])
def get_user_apoyos(user_id):
    user = Usuario.query.get(user_id)
    if not user: return jsonify({'message': 'Usuario no encontrado'}), 404

    try:
        supported_reports = db.session.query(Reporte).join(Apoyo).filter(
            Apoyo.usuario_id == user_id,
            Apoyo.tipo == 'like'
        ).all()
        
        report_list = [report.to_dict(
            current_user_id=user_id, 
            current_user_role='usuario'
        ) for report in supported_reports]
        
        return jsonify(report_list), 200
    except Exception as e:
        print(f"Error fetching user apoyos: {e}")
        return jsonify({'message': 'Error interno al obtener los apoyos del usuario'}), 500

@main.route('/usuarios/<int:user_id>/denuncias', methods=['GET']) #esto esta para los apoyos 
def get_user_denuncias(user_id):
    user = Usuario.query.get(user_id)
    if not user: return jsonify({'message': 'Usuario no encontrado'}), 404

    try:
        disliked_reports = db.session.query(Reporte).join(Apoyo).filter(
            Apoyo.usuario_id == user_id,
            Apoyo.tipo == 'dislike'
        ).all()

        report_list = [report.to_dict(
            current_user_id=user_id, 
            current_user_role='usuario'
        ) for report in disliked_reports]

        return jsonify(report_list), 200
    except Exception as e:
        print(f"Error fetching user denuncias: {e}")
        return jsonify({'message': 'Error interno al obtener las denuncias del usuario'}), 500

@main.route('/funcionarios/<int:func_id>/apoyos', methods=['GET'])
def get_funcionario_apoyos(func_id):
    funcionario = Funcionario.query.get(func_id)
    if not funcionario: return jsonify({'message': 'Funcionario no encontrado'}), 404

    try:
        supported_reports = db.session.query(Reporte).join(Apoyo).filter(
            Apoyo.funcionario_id == func_id,
            Apoyo.tipo == 'like'
        ).all()
        
        report_list = [report.to_dict(
            current_user_id=func_id, 
            current_user_role='funcionario'
        ) for report in supported_reports]
        
        return jsonify(report_list), 200
    except Exception as e:
        print(f"Error fetching funcionario apoyos: {e}")
        return jsonify({'message': 'Error interno al obtener los apoyos del funcionario'}), 500

@main.route('/funcionarios/<int:func_id>/denuncias', methods=['GET'])
def get_funcionario_denuncias(func_id):
    funcionario = Funcionario.query.get(func_id)
    if not funcionario: return jsonify({'message': 'Funcionario no encontrado'}), 404

    try:
        disliked_reports = db.session.query(Reporte).join(Apoyo).filter(
            Apoyo.funcionario_id == func_id,
            Apoyo.tipo == 'dislike'
        ).all()

        report_list = [report.to_dict(
            current_user_id=func_id, 
            current_user_role='funcionario'
        ) for report in disliked_reports]

        return jsonify(report_list), 200
    except Exception as e:
        print(f"Error fetching funcionario denuncias: {e}")
        return jsonify({'message': 'Error interno al obtener las denuncias del funcionario'}), 500
    
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
    # 1. Obtener el ID de usuario desde los parámetros de la URL
    user_id = request.args.get('user_id')

    # 2. Validación
    if not user_id:
        return jsonify({'error': 'El parámetro user_id es obligatorio.'}), 400
    try:
        user_id_int = int(user_id)
    except ValueError:
        return jsonify({'error': 'El user_id debe ser un número entero válido.'}), 400

    # 3. Consultar la base de datos (con JOIN)
    try:
        # Usamos db.session.query() para seleccionar ambas tablas
        # y .join() para unirlas por el categoria_id.
        reportes_con_categoria = db.session.query(Reporte, Categoria).join(
            Categoria, Reporte.categoria_id == Categoria.id
        ).filter(
            Reporte.usuario_creador_id == user_id_int
        ).all()
        # ----------------------------

        resultado_formateado = []
        
        # Ahora iteramos sobre una lista de tuplas (reporte, categoria)
        for reporte, categoria in reportes_con_categoria:
            resultado_formateado.append({
                "id": reporte.id,
                "nombre": reporte.tipo_evento,
                "img_prueba_1": reporte.img_prueba_1,
                "fecha_creacion": reporte.fecha_creacion.isoformat() if reporte.fecha_creacion else None,
                "direccion": reporte.direccion,
                "estado": reporte.estado,
                "categoria_nombre": categoria.nombre 
            })

        return jsonify(resultado_formateado), 200

    except Exception as e:
        print(f"Error en /misreportes: {e}")
        return jsonify({'error': 'Ocurrió un error en el servidor.'}), 500
    

@main.route('/reportes/<int:reporte_id>', methods=['GET','DELETE'])
def reportes(reporte_id):
    reporte = Reporte.query.get_or_404(reporte_id)
    
    # --- LA CORRECCIÓN ESTÁ AQUÍ ---
    # Lee 'user_id' desde los argumentos de la URL (ej. ?user_id=123)
    user_id = request.args.get('user_id', type=int) 
    # Lee 'User-Role' desde los headers (como ya lo tenías)
    user_role = request.headers.get('User-Role', 'usuario')

    if request.method == 'DELETE':
        try:
            reporte_a_eliminar = Reporte.query.get(reporte_id)

            if reporte_a_eliminar is None:
                return jsonify({'error': 'Reporte no encontrado.'}), 404

            if reporte_a_eliminar.estado not in ['Nuevo', 'Resuelto']:
                return jsonify({'error': 'No se puede eliminar un reporte que está en proceso.'}), 403

            db.session.delete(reporte_a_eliminar)
            db.session.commit()

            return jsonify({'message': 'Reporte eliminado exitosamente.'}), 200

        except Exception as e:
            db.session.rollback()
            print(f"Error en DELETE /reportes/<id>: {e}")
            return jsonify({'error': 'Ocurrió un error en el servidor.'}), 500
    else:
        try:
            reporte_data = reporte.to_dict(
                current_user_id=user_id, 
                current_user_role=user_role
            )
            return jsonify(reporte_data), 200
        
        except Exception as e:
            print(f"Error al serializar el reporte {reporte_id}: {e}")
            return jsonify({"error": "Error interno al procesar el reporte"}), 500

            


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

#Comentarios handling 
@main.route('/reportes/<int:reporte_id>/comentarios', methods=['GET'])
def get_comentarios(reporte_id):
    comentarios = Comentario.query.filter_by(reporte_id=reporte_id).order_by(Comentario.fecha_creacion.desc()).all()
    return jsonify([c.to_dict() for c in comentarios]), 200

@main.route('/reportes/<int:reporte_id>/comentarios', methods=['POST'])
def post_comentario(reporte_id):
    data = request.get_json()
    
    # JWT TOKEN REALMENTE NO TENEMOS ASI QUE
    # Por ahora, lo pasamos desde la app
    usuario_id = data.get('usuario_id')
    if not usuario_id:
        return jsonify({"error": "usuario_id es requerido"}), 400

    try:
        nuevo_comentario = Comentario(
            texto=data['texto'],
            reporte_id=reporte_id,
            usuario_id=usuario_id
        )
        db.session.add(nuevo_comentario)
        db.session.commit()
        return jsonify(nuevo_comentario.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@main.route('/comentarios/<int:comentario_id>', methods=['PUT'])
def update_comentario(comentario_id):
    comentario = Comentario.query.get_or_404(comentario_id)
    # TODO: Añadir lógica de permisos (solo el autor puede editar)
    
    data = request.get_json()
    comentario.texto = data.get('texto', comentario.texto)
    db.session.commit()
    return jsonify(comentario.to_dict()), 200

@main.route('/comentarios/<int:comentario_id>', methods=['DELETE'])
def delete_comentario(comentario_id):
    comentario = Comentario.query.get_or_404(comentario_id)
    # TODO: Añadir lógica de permisos (solo el autor puede eliminar) XD MAÑANA MIRAMO

    db.session.delete(comentario)
    db.session.commit()
    return jsonify({"message": "Comentario eliminado"}), 200