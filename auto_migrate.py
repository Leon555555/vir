import os
from app import create_app
from app.extensions import db
from app.models import Coach

app = create_app()

with app.app_context():
    print("🔄 Ejecutando migraciones automáticas...")

    try:
        # Forzar creación de tablas
        db.create_all()
        print("✅ Tablas creadas correctamente.")

        # Crear usuario inicial 'Vale' si no existe
        if not Coach.query.filter_by(email="vale@vir.app").first():
            vale = Coach(
                email="vale@vir.app",
                nombre="Valentina",
                apodo="Bichito de luz",
            )
            vale.set_password("vale123")
            db.session.add(vale)
            db.session.commit()
            print("🌸 Usuario 'Vale' creado correctamente.")
        else:
            print("ℹ️ Usuario 'Vale' ya existe, no se creó nuevamente.")
    except Exception as e:
        print(f"⚠️ Error durante migración: {e}")
