from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

with app.app_context():
    db.create_all()
    print("✅ Tablas creadas o ya existentes.")

    # Crear usuario entrenador Viru si no existe
    if not User.query.filter_by(email="viru@vir.app").first():
        viru = User(nombre="Viru", email="viru@vir.app", grupo="Entrenador")
        viru.set_password("Virulana369")
        db.session.add(viru)
        db.session.commit()
        print("🏋️‍♂️ Usuario entrenador 'Viru' creado correctamente.")
    else:
        print("✅ Usuario 'Viru' ya existe.")

if __name__ == "__main__":
    app.run(debug=True)
