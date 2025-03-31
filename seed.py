from app import create_app
from app.models import db, Coach

app = create_app()

with app.app_context():
    db.create_all()

    # Crear coach por defecto si no existe
    if not Coach.query.filter_by(email="admin@urban.com").first():
        coach = Coach(email="admin@urban.com")
        coach.set_password("admin123")  # Puedes cambiar la contraseña
        db.session.add(coach)
        db.session.commit()
        print("✅ Coach creado: admin@urban.com / admin123")
    else:
        print("ℹ️ Coach ya existente")
