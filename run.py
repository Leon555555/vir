from app import create_app
from app.models import db, Coach
from werkzeug.security import generate_password_hash
from app.models import Atleta
app = create_app()

# Esta sección se ejecuta cuando se lanza la app
with app.app_context():
    # Crear todas las tablas si no existen
    db.create_all()

    # Crear coach por defecto si no existe
    if not Coach.query.filter_by(email="admin@urban.com").first():
        coach = Coach(
            email="admin@urban.com",
            password_hash=generate_password_hash("admin123")
        )
        db.session.add(coach)
        db.session.commit()
# Agrega atletas si no hay
with app.app_context():
    if Atleta.query.count() == 0:
        demo = Atleta(nombre='Juan Pérez', email='juan@example.com', telefono='123456789')
        db.session.add(demo)
        db.session.commit()
        print("✅ Atleta demo creado")
from app.models import Coach, db

with app.app_context():
    db.create_all()

    if not Coach.query.filter_by(email="admin@urban.com").first():
        coach = Coach(email="admin@urban.com")
        coach.set_password("admin123")
        db.session.add(coach)
        db.session.commit()
        print("✅ Coach creado en Render")
