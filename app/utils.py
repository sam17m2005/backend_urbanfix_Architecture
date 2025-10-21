import base64
import io
import uuid # Para generar nombres de archivo únicos
from PIL import Image
from flask import request, jsonify 
from config import Config
from . import s3_client

# --- Cliente S3 y Configuración del Bucket ---
S3_REPORTES = Config.S3_REPORTES 

def upload_base64_to_s3(base64_string):
    if not base64_string: #Esta monda cambia el focking base64  a imagen 
        return None

    try:
        if ',' in base64_string:
            _, encoded_data = base64_string.split(',', 1)
        else:
            encoded_data = base64_string
            
        image_bytes = base64.b64decode(encoded_data)
        image = Image.open(io.BytesIO(image_bytes))
        output_buffer = io.BytesIO()
        image.save(output_buffer, format='PNG')
        output_buffer.seek(0)

        file_name = f"{uuid.uuid4()}.png"

        s3_client.upload_fileobj(
            output_buffer,
            S3_REPORTES,
            file_name,
            ExtraArgs={'ContentType': 'image/png'}
        )
        
        s3_url = f"https://{S3_REPORTES}.s3.{Config.AWS_REGION}.amazonaws.com/{file_name}"
        return s3_url

    except Exception as e:
        print(f"Error al subir a S3: {e}")
        return None