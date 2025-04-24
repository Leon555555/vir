import os

class Config:
    # Si está definida la variable de entorno DATABASE_URL (como en Render), se usa esa
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///urban.db')

    # Evita advertencias de SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Clave secreta para sesiones
    SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_de_desarollo')

    # Activar modo debug si está en desarrollo
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    # Entorno: puede ser 'production' o 'development'
    ENV = os.environ.get('FLASK_ENV', 'production')

