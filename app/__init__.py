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
