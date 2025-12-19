# run.py
from __future__ import annotations

import os
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

def patch_schema():
    """
    ✅ Parcha la DB en producción si faltan columnas.
    No rompe el arranque si algo falla.
    """
    stmts = [
        # Fix principal (tu error actual)
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;",

        # Fix Strava (para que no vuelva a romper luego)
        "ALTER TABLE integration_accounts ADD COLUMN IF NOT EXISTS external_user_id VARCHAR(80);",
        "ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS provider_activity_id VARCHAR(80);",
    ]

    for s in stmts:
        try:
            db.session.execute(text(s))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"⚠️ No se pudo ejecutar: {s}\n⚠️ {e}")

with app.app_context():
    # 1) ✅ arregla columnas faltantes
    patch_schema()

    # 2) ✅ bootstrap admin SIN romper si hay problemas
    try:
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@vir.app").strip().lower()
        admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")

        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(nombre="Admin", email=admin_email, grupo="admin")
            admin.set_password(admin_pass)
            admin.is_admin = True
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin creado")
        else:
            # aseguramos flag
            if getattr(admin, "is_admin", False) is False:
                admin.is_admin = True
                db.session.commit()
            print("✅ Admin ya existe")

    except ProgrammingError as e:
        db.session.rollback()
        print("⚠️ ProgrammingError en bootstrap admin (no crítico).")
        print(e)

    except Exception as e:
        db.session.rollback()
        print("⚠️ Error en bootstrap admin (no crítico).")
        print(e)
