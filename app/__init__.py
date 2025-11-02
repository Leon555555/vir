import os
from flask import Flask
from flask_login import LoginManager
from app.extensions import db, migrate
from app.models import User

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave-ultra-segura")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://vir_db_user:bRbsLtpZ3I4rag19scmcAfRyXjZVNsUw@dpg-d3vtoc75r7bs73ch4bc0-a/vir_db",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Uploads (LOCAL dev). En Render: usar URLs (Cloudinary/S3).
    app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "app/static/uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB
    app.config["ALLOWED_IMAGE_EXT"] = {"png", "jpg", "jpeg", "webp", "gif"}
    app.config["ALLOWED_VIDEO_EXT"] = {"mp4", "webm", "mov", "m4v"}

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # semilla admin
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(email="admin@vir.app").first()
        if not admin:
            admin = User(nombre="Admin ViR", email="admin@vir.app", grupo="Entrenador")
            admin.set_password("vir2025")
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin creado: admin@vir.app / vir2025")
        else:
            print("✅ Admin ya existe.")

    return app
