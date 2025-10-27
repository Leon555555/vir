import os
from flask import Flask
from .extensions import db, migrate, login_manager
from config import Config

# Cargar variables de entorno desde .env si no estamos en producción
if os.getenv("FLASK_ENV") != "production":
    from dotenv import load_dotenv
    load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Registrar blueprints
    from .routes import main_bp
    app.register_blueprint(main_bp)

    # Crear atleta demo solo si estamos en entorno de desarrollo
    if app.config.get("ENV") == "development":
        with app.app_context():
            from .models import Atleta
            if not Atleta.query.filter_by(email='lvidelaramos@gmail.com').first():
                nuevo = Atleta(
                    nombre='Leandro Videla',
                    email='lvidelaramos@gmail.com',
                    telefono='123456789',
                    edad=30,
                    altura=175,
                    peso=70
                )
                db.session.add(nuevo)
                db.session.commit()

    return app
