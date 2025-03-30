from app import create_app
from app.models import db, Coach
from werkzeug.security import generate_password_hash

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
