from app import create_app
from app.models import db, Coach

app = create_app()

# Crear coach solo si no existe
with app.app_context():
    if not Coach.query.filter_by(email="admin@urban.com").first():
        coach = Coach(email="admin@urban.com")
        coach.set_password("1234")  # Cambia esto luego por seguridad
        db.session.add(coach)
        db.session.commit()
        print("✅ Coach creado automáticamente")

# Arranca el servidor (Render ya usa gunicorn, así que esto es solo local)
if __name__ == '__main__':
    app.run(debug=True)
