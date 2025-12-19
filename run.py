# run.py
from __future__ import annotations

import os
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

def safe_exec(sql: str):
    try:
        db.session.execute(text(sql))
        db.session.commit()
        print(f"✅ SQL OK: {sql}")
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ SQL FAIL: {sql}\n⚠️ {e}")

def patch_schema():
    """
    ✅ Parchea esquema en producción (sin migraciones)
    - users: is_admin, fecha_creacion
    - integration_accounts: external_user_id
    - external_activities: provider_activity_id
    """
    # USERS
    safe_exec("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
    safe_exec("ALTER TABLE users ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW();")

    # STRAVA
    safe_exec("ALTER TABLE integration_accounts ADD COLUMN IF NOT EXISTS external_user_id VARCHAR(80);")
    safe_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS provider_activity_id VARCHAR(80);")

with app.app_context():
    # 1) ✅ arregla columnas faltantes
    patch_schema()

    # 2) ✅ crea/asegura admin sin romper el arranque
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
            if getattr(admin, "is_admin", False) is False:
                admin.is_admin = True
                db.session.commit()
            print("✅ Admin ya existe")

    except Exception as e:
        db.session.rollback()
        print("⚠️ Error creando/verificando admin (no crítico):", e)
