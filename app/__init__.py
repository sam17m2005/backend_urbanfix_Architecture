from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
import boto3
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

# Se crea una sola vez
s3_client = boto3.client(
    "s3",
    aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
    region_name=Config.AWS_REGION
)
  
def create_app():
    """Crea y configura una instancia de la aplicación Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Importamos y registramos las rutas
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app