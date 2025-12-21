# app/__init__.py
from flask import Flask
from flask_login import LoginManager

from app.extensions import db
from app.config import Config

def create_app() -> Flask:
    app = Flask(__name__)

    # Config
    app.config.from_object(Config)

    # 🔥 Si no hay DB, error CLARO
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError(
            "Falta DATABASE_URL o SQLALCHEMY_DATABASE_URI en variables de entorno."
        )

    # DB init
    db.init_app(app)

    # Login init
    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # Blueprint
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app
