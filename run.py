# run.py
from __future__ import annotations

import os
from sqlalchemy.exc import ProgrammingError

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

# ✅ BLINDADO: nunca mates el arranque por DB desfasada
with app.app_context():
    try:
        # Si tu DB está vieja y falta users.is_admin, acá petaba.
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@vir.app").strip().lower()
        admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")

        admin = User.query.filter_by(email=admin_email).first()

        if not admin:
            admin = User(nombre="Admin", email=admin_email, grupo="admin")
            admin.set_password(admin_pass)
            # setear is_admin si existe en el modelo
            if hasattr(admin, "is_admin"):
                admin.is_admin = True
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin creado")
        else:
            print("✅ Admin ya existe")

    except ProgrammingError as e:
        db.session.rollback()
        print("⚠️ DB no migrada todavía (faltan columnas). La app arranca igual.")
        print(f"⚠️ Detalle: {e}")

    except Exception as e:
        db.session.rollback()
        print("⚠️ Error en bootstrap admin (no crítico). La app arranca igual.")
        print(f"⚠️ Detalle: {e}")
