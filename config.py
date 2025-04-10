import os

class Config:
    # Base de datos: toma la de entorno (Render) o usa SQLite en local
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///urban.db')

    # Evita warnings de SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Clave secreta para sesiones y seguridad
    SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_de_desarollo')

    # Modo debug opcional
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'secreto')
    ENV = os.environ.get('FLASK_ENV', 'production')  # ← esta línea nueva
