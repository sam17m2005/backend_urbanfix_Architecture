from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Se crea la instancia de la base de datos sin vincularla a una app todavía
db = SQLAlchemy()

def create_app():
    """Crea y configura una instancia de la aplicación Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inicializa la base de datos con la configuración de la app
    db.init_app(app)
    
    # Importar y registrar las rutas (Blueprints)
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app