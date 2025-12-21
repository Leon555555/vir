# app/__init__.py
from flask import Flask
from app.extensions import db
from flask_login import LoginManager

def create_app():
    app = Flask(__name__)

    # ---- tu config ----
    # app.config.from_object(...)
    # app.config["SECRET_KEY"] = ...
    # -------------------

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ✅ registrar blueprint único "main"
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app
