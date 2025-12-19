# auto_migrate.py
from __future__ import annotations

import os
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()


def table_exists(table: str) -> bool:
    q = text("SELECT to_regclass(:t)")
    return db.session.execute(q, {"t": f"public.{table}"}).scalar() is not None


def sql_exec(sql: str):
    try:
        db.session.execute(text(sql))
        db.session.commit()
        print("✅ SQL OK:", " ".join(sql.strip().split()))
    except Exception as e:
        db.session.rollback()
        print("❌ SQL ERROR:", str(e))


def ensure_admin():
    admin = User.query.filter_by(email="admin@vir.app").first()
    if not admin:
        admin = User(nombre="Admin", email="admin@vir.app", grupo="ADMIN", is_admin=True)
        admin.set_password(os.environ.get("ADMIN_PASSWORD", "admin1234"))
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin creado")
    else:
        if not admin.is_admin:
            admin.is_admin = True
            db.session.commit()
        print("✅ Admin ya existe")


with app.app_context():
    print("🔄 AUTO MIGRATE: create_all + fix_schema + ensure_admin")

    # 1) Crear tablas faltantes (rutinas, athlete_logs, athlete_checks, etc.)
    try:
        db.create_all()
        print("✅ db.create_all() OK (tablas creadas/verificadas).")
    except Exception as e:
        print(f"⚠️ Error en create_all: {e}")

    # 2) Arreglar columnas users (si existen)
    if table_exists("users"):
        sql_exec("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
        sql_exec("ALTER TABLE users ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW();")

    # 3) Fix FK dia_plan -> users (limpieza de huérfanos + FK)
    if table_exists("dia_plan"):
        sql_exec("""
            DELETE FROM dia_plan dp
            WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = dp.user_id);
        """)
        sql_exec("ALTER TABLE dia_plan DROP CONSTRAINT IF EXISTS dia_plan_user_id_fkey;")
        sql_exec("""
            ALTER TABLE dia_plan
            ADD CONSTRAINT dia_plan_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE;
        """)

    # 4) Fix FK athlete_logs / athlete_checks si existen
    if table_exists("athlete_logs"):
        sql_exec("ALTER TABLE athlete_logs DROP CONSTRAINT IF EXISTS athlete_logs_user_id_fkey;")
        sql_exec("""
            ALTER TABLE athlete_logs
            ADD CONSTRAINT athlete_logs_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE;
        """)

    if table_exists("athlete_checks"):
        sql_exec("ALTER TABLE athlete_checks DROP CONSTRAINT IF EXISTS athlete_checks_user_id_fkey;")
        sql_exec("""
            ALTER TABLE athlete_checks
            ADD CONSTRAINT athlete_checks_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE;
        """)

    # 5) Admin
    try:
        ensure_admin()
    except Exception as e:
        print(f"⚠️ Error creando admin: {e}")
