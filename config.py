import os

class Config:
    # Corrige URLs antiguas (Render puede dar 'postgres://' en lugar de 'postgresql://')
    uri = os.environ.get("DATABASE_URL", "sqlite:///urban.db")
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_de_desarollo')
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    ENV = os.environ.get('FLASK_ENV', 'production')
