from app import create_app
from app.models import db, Coach
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    db.create_all()  # 👈 esto crea las tablas si no existen

    # Solo si no existe aún el coach
    if not Coach.query.filter_by(email="admin@urban.com").first():
        coach = Coach(email="admin@urban.com", password_hash=generate_password_hash("admin123"))
        db.session.add(coach)
        db.session.commit()
