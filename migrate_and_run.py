from app import app
from flask_migrate import upgrade

# Ejecutar migraciones pendientes antes de iniciar la app
with app.app_context():
    upgrade()

# Luego levantar Gunicorn como lo harías normalmente
import os
os.system("gunicorn run:app")
