import os

class Config:
    # Intentar usar la variable de entorno DATABASE_URL (Render la crea automáticamente)
    uri = os.environ.get("DATABASE_URL")
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = uri or "sqlite:///urban.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "clave_de_desarollo")
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    ENV = os.environ.get("FLASK_ENV", "production")
