from app import create_app, db
from app.models import User
from datetime import datetime
import psycopg2
import os

app = create_app()

def ensure_db_structure():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL no configurada.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        # --- user.fecha_creacion ---
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='user' AND column_name='fecha_creacion';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando columna user.fecha_creacion ...")
            cur.execute("""ALTER TABLE "user" ADD COLUMN fecha_creacion TIMESTAMP DEFAULT NOW();""")
            conn.commit()

        # --- rutina.tipo ---
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='rutina' AND column_name='tipo';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando columna rutina.tipo ...")
            cur.execute("""ALTER TABLE rutina ADD COLUMN tipo VARCHAR(100) DEFAULT 'General';""")
            conn.commit()

        # --- rutina_item.ejercicio_id (si no existe) ---
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='rutina_item' AND column_name='ejercicio_id';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando columna rutina_item.ejercicio_id ...")
            cur.execute("""ALTER TABLE rutina_item ADD COLUMN ejercicio_id INTEGER;""")
            conn.commit()

        # --- rutina_item.nota (si no existe) ---
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='rutina_item' AND column_name='nota';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando columna rutina_item.nota ...")
            cur.execute("""ALTER TABLE rutina_item ADD COLUMN nota TEXT;""")
            conn.commit()

        # --- dia_plan.puede_entrenar (si no existe) ---
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='dia_plan' AND column_name='puede_entrenar';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando columna dia_plan.puede_entrenar ...")
            cur.execute("""ALTER TABLE dia_plan ADD COLUMN puede_entrenar VARCHAR(50);""")
            conn.commit()

        # --- athlete_check table ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS athlete_check (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                fecha DATE NOT NULL,
                rutina_item_id INTEGER NOT NULL REFERENCES rutina_item(id) ON DELETE CASCADE,
                done BOOLEAN NOT NULL DEFAULT TRUE,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, fecha, rutina_item_id)
            );
        """)
        conn.commit()

        # --- athlete_log table ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS athlete_log (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                fecha DATE NOT NULL,
                did_train BOOLEAN NOT NULL DEFAULT FALSE,
                warmup_done TEXT,
                main_done TEXT,
                finisher_done TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, fecha)
            );
        """)
        conn.commit()

        cur.close()
        conn.close()
        print("✅ Estructura de base sincronizada.")

    except Exception as e:
        print("⚠️ Error verificando estructura:", e)

ensure_db_structure()

# --- Crear admin si no existe ---
with app.app_context():
    db.create_all()

    admin_email = "admin@vir.app"
    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            nombre="Admin",
            email=admin_email,
            grupo="Entrenador",
            fecha_creacion=datetime.utcnow(),
        )
        admin.set_password("V!ru_Admin-2025$X9")
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin creado correctamente.")
    else:
        print("✅ Admin ya existe.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
