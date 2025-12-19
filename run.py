# run.py
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


def bootstrap_tables_if_needed():
    # SOLO para la primera vez o cuando agregás tablas nuevas
    if os.getenv("AUTO_CREATE_DB", "0") == "1":
        try:
            db.create_all()
            print("✅ db.create_all() ejecutado (AUTO_CREATE_DB=1).")
        except Exception as e:
            print(f"⚠️ No se pudo ejecutar db.create_all(): {e}")
    else:
        print("ℹ️ AUTO_CREATE_DB=0: no se ejecuta db.create_all().")


def fix_schema():
    # users columns
    if table_exists("users"):
        sql_exec("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
        sql_exec("ALTER TABLE users ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW();")

    # dia_plan FK (limpia huérfanos antes)
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

    # athlete_logs FK
    if table_exists("athlete_logs"):
        sql_exec("ALTER TABLE athlete_logs DROP CONSTRAINT IF EXISTS athlete_logs_user_id_fkey;")
        sql_exec("""
            ALTER TABLE athlete_logs
            ADD CONSTRAINT athlete_logs_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE;
        """)

    # athlete_checks FK
    if table_exists("athlete_checks"):
        sql_exec("ALTER TABLE athlete_checks DROP CONSTRAINT IF EXISTS athlete_checks_user_id_fkey;")
        sql_exec("""
            ALTER TABLE athlete_checks
            ADD CONSTRAINT athlete_checks_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE;
        """)

    # -------------------------
    # STRAVA: columnas faltantes
    # -------------------------
    if table_exists("integration_accounts"):
        sql_exec("ALTER TABLE integration_accounts ADD COLUMN IF NOT EXISTS external_user_id VARCHAR(80);")

    if table_exists("external_activities"):
        # create_all NO agrega columnas si ya existe la tabla
        sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS start_date TIMESTAMP;")
        sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS distance_m DOUBLE PRECISION;")
        sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS moving_time_s INTEGER;")
        sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS elapsed_time_s INTEGER;")
        sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS raw_json JSON;")
        sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();")
        sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();")


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
    bootstrap_tables_if_needed()
    fix_schema()
    ensure_admin()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
