# run.py
from __future__ import annotations

import os

from app import create_app
from app.extensions import db
from app.models import User

from app.schema_fix import fix_schema  # ✅ usamos el mismo fix

app = create_app()


def bootstrap_tables_if_needed():
    if os.getenv("AUTO_CREATE_DB", "0") == "1":
        try:
            db.create_all()
            print("✅ db.create_all() ejecutado (AUTO_CREATE_DB=1).")
        except Exception as e:
            print(f"⚠️ No se pudo ejecutar db.create_all(): {e}")
    else:
        print("ℹ️ AUTO_CREATE_DB=0: no se ejecuta db.create_all().")


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
