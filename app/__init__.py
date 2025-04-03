import os
from flask import Flask
from .extensions import db
from config import Config
from dotenv import load_dotenv

# Carga las variables del .env (solo en desarrollo/local)
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    return app
with app.app_context():
    from .models import Atleta, db

    # Verificamos si ya existe
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
