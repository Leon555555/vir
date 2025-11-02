from flask import Flask
from flask_login import LoginManager
from app.extensions import db
from app.models import User
from datetime import datetime


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "clave-ultra-segura"

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = "postgresql://vir_db_user:bRbsLtpZ3I4rag19scmcAfRyXjZVNsUw@dpg-d3vtoc75r7bs73ch4bc0-a/vir_db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow}

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app
