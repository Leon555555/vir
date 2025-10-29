from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# =============================
# 📦 EXTENSIONES COMPARTIDAS
# =============================
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# Configuración general de Flask-Login
login_manager.login_view = "main.login"
login_manager.login_message = "Por favor, inicia sesión para continuar."
