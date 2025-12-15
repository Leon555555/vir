# run.py
from datetime import datetime
import os
import psycopg2

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()


def ensure_columns():
    """
    Render + Postgres: si no usás migrations, esto te evita que se caiga el deploy
    cuando agregás columnas nuevas.
    """
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL no configurada.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        def col_exists(table: str, col: str) -> bool:
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name=%s AND column_name=%s
                """,
                (table, col),
            )
            return cur.fetchone() is not None

        # -------- USER
        if col_exists("user", "fecha_creacion") is False:
            print("🛠️ Agregando user.fecha_creacion...")
            cur.execute("""ALTER TABLE "user" ADD COLUMN fecha_creacion TIMESTAMP DEFAULT NOW();""")
            conn.commit()

        if col_exists("user", "is_admin") is False:
            print("🛠️ Agregando user.is_admin...")
            cur.execute("""ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;""")
            conn.commit()

        # -------- RUTINA
        if col_exists("rutina", "tipo") is False:
            print("🛠️ Agregando rutina.tipo...")
            cur.execute("""ALTER TABLE rutina ADD COLUMN tipo VARCHAR(100) DEFAULT 'General';""")
            conn.commit()

        # -------- DIA_PLAN (bloqueo atleta)
        if col_exists("dia_plan", "puede_entrenar") is False:
            print("🛠️ Agregando dia_plan.puede_entrenar...")
            cur.execute("""ALTER TABLE dia_plan ADD COLUMN puede_entrenar VARCHAR(10) DEFAULT 'si';""")
            conn.commit()

        if col_exists("dia_plan", "comentario_atleta") is False:
            print("🛠️ Agregando dia_plan.comentario_atleta...")
            cur.execute("""ALTER TABLE dia_plan ADD COLUMN comentario_atleta TEXT;""")
            conn.commit()

        print("✅ Estructura de base sincronizada.")
        cur.close()
        conn.close()

    except Exception as e:
        print("⚠️ Error verificando estructura:", e)


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
