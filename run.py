from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
from app import create_app
from app.extensions import db
from app.models import Coach, Atleta  # importa todos tus modelos

app = create_app()

# 🔧 Crea las tablas automáticamente si no existen
with app.app_context():
    db.create_all()
    print("✅ Tablas creadas o ya existentes.")
