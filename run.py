# run.py
from __future__ import annotations

import os
import psycopg2
from psycopg2 import sql

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()


def ensure_columns():
    """
    Render + Postgres (sin migrations):
    - Crea/actualiza columnas críticas si faltan para evitar caídas en deploy.
    """
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL no configurada.")
        return

    conn = None
    cur = None

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        def col_exists(table: str, col: str, schema: str = "public") -> bool:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema=%s AND table_name=%s AND column_name=%s
                """,
                (schema, table, col),
            )
            return cur.fetchone() is not None

        def add_col(query: str, msg: str):
            print(msg)
            cur.execute(query)
            conn.commit()

        # ---------------- USER
        if not col_exists("user", "fecha_creacion"):
            add_col(
                """ALTER TABLE "user" ADD COLUMN fecha_creacion TIMESTAMP DEFAULT NOW();""",
                "🛠️ Agregando user.fecha_creacion...",
            )

        if not col_exists("user", "is_admin"):
            add_col(
                """ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;""",
                "🛠️ Agregando user.is_admin...",
            )

        # ---------------- RUTINA
        if not col_exists("rutina", "tipo"):
            add_col(
                """ALTER TABLE rutina ADD COLUMN tipo VARCHAR(100) DEFAULT 'General';""",
                "🛠️ Agregando rutina.tipo...",
            )

        # ✅ FIX DEL ERROR: rutina.created_at
        if not col_exists("rutina", "created_at"):
            add_col(
                """ALTER TABLE rutina ADD COLUMN created_at TIMESTAMP DEFAULT NOW();""",
                "🛠️ Agregando rutina.created_at...",
            )

        # ---------------- DIA_PLAN (bloqueo atleta)
        if not col_exists("dia_plan", "puede_entrenar"):
            add_col(
                """ALTER TABLE dia_plan ADD COLUMN puede_entrenar VARCHAR(10) DEFAULT 'si';""",
                "🛠️ Agregando dia_plan.puede_entrenar...",
            )

        if not col_exists("dia_plan", "comentario_atleta"):
            add_col(
                """ALTER TABLE dia_plan ADD COLUMN comentario_atleta TEXT;""",
                "🛠️ Agregando dia_plan.comentario_atleta...",
            )

        print("✅ Estructura de base sincronizada.")

    except Exception as e:
        if conn:
            conn.rollback()
        print("⚠️ Error verificando estructura:", e)

    finally:
        try:
            if cur:
                cur.close()
        finally:
            if conn:
                conn.close()


ensure_columns()

with app.app_context():
    db.create_all()

    admin = User.query.filter_by(email="admin@vir.app").first()
    if not admin:
        admin = User(
            nombre="Admin",
            email="admin@vir.app",
            grupo="Entrenador",
            is_admin=True,
        )
        admin.set_password("V!ru_Admin-2025$X9")
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin creado correctamente.")
    else:
        # por si existía viejo sin is_admin
        if not getattr(admin, "is_admin", False):
            admin.is_admin = True
            db.session.commit()
        print("✅ Admin ya existe.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
