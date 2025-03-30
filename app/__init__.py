from flask import Flask
from .extensions import db

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:leander369@localhost/urban_athletics'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'secreto'

    db.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    return app
