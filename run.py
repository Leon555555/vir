# run.py
from __future__ import annotations

import os
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

def sql_exec(sql: str):
    try:
        db.session.execute(text(sql))
        db.session.commit()
        print("✅ SQL OK:", sql.strip().replace("\n", " "))
    except Exception as e:
        db.session.rollback()
        print("❌ SQL ERROR:", str(e))

def fix_schema():
    # ✅ columnas (lo que ya venías haciendo)
    sql_exec("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
    sql_exec("ALTER TABLE users ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW();")

    # ✅ FK correcto: dia_plan.user_id -> users.id
    sql_exec("ALTER TABLE dia_plan DROP CONSTRAINT IF EXISTS dia_plan_user_id_fkey;")
    sql_exec("""
        ALTER TABLE dia_plan
        ADD CONSTRAINT dia_plan_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE;
    """)

    # ✅ si existe athlete_logs / athlete_checks, arreglamos también
    sql_exec("ALTER TABLE athlete_logs DROP CONSTRAINT IF EXISTS athlete_logs_user_id_fkey;")
    sql_exec("""
        ALTER TABLE athlete_logs
        ADD CONSTRAINT athlete_logs_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE;
    """)

    sql_exec("ALTER TABLE athlete_checks DROP CONSTRAINT IF EXISTS athlete_checks_user_id_fkey;")
    sql_exec("""
        ALTER TABLE athlete_checks
        ADD CONSTRAINT athlete_checks_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE;
    """)

def ensure_admin():
    admin = User.query.filter_by(email="admin@vir.app").first()
    if not admin:
        admin = User(nombre="Admin", email="admin@vir.app", grupo="ADMIN", is_admin=True)
        admin.set_password(os.environ.get("ADMIN_PASSWORD", "admin1234"))
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin creado")
    else:
        # por si existía pero sin flag
        if not admin.is_admin:
            admin.is_admin = True
            db.session.commit()
        print("✅ Admin ya existe")

with app.app_context():
    fix_schema()
    ensure_admin()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
