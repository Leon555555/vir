from app import app
from flask_migrate import upgrade

if __name__ == "__main__":
    with app.app_context():
        print("🛠️ Ejecutando migraciones automáticas...")
        upgrade()
        print("✅ Migraciones aplicadas con éxito.")

