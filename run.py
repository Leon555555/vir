from app import create_app
from app.extensions import db
from app.models import User  # modelo multiusuario principal

app = create_app()

# 🔧 Crea las tablas automáticamente si no existen
with app.app_context():
    db.create_all()
    print("✅ Tablas creadas o ya existentes.")

    # Crear usuario Vale automáticamente si no existe
    if not User.query.filter_by(email="vale@vir.app").first():
        vale = User(nombre="Valeria", email="vale@vir.app")
        vale.set_password("vale123")
        db.session.add(vale)
        db.session.commit()
        print("🌸 Usuario 'Vale' creado correctamente.")
    else:
        print("✅ Usuario 'Vale' ya existe.")

if __name__ == "__main__":
    app.run(debug=True)
