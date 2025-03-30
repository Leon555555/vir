from app import create_app
from app.extensions import db
from app.models import db, Atleta, Entrenamiento, Mensaje  # asegurate de importar Mensaje

app = create_app()

with app.app_context():
    db.create_all()
    print("✅ Tablas creadas correctamente.")

app = create_app()

with app.app_context():
    db.create_all()
    print("Tablas creadas correctamente.")
