from app import create_app, db
from app.models import User
from datetime import datetime
import psycopg2, os

app = create_app()

def ensure_columns():
    """Verifica columnas/tablas críticas y las crea si faltan (idempotente)."""
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL no configurada.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        # ----------------------------
        # 1) user.fecha_creacion
        # ----------------------------
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='user' AND column_name='fecha_creacion';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando columna 'fecha_creacion' a user...")
            cur.execute("""ALTER TABLE "user" ADD COLUMN fecha_creacion TIMESTAMP DEFAULT NOW();""")
            conn.commit()

        # ----------------------------
        # 2) user.is_admin  ✅ (LO QUE TE ROMPIÓ EN RENDER)
        # ----------------------------
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='user' AND column_name='is_admin';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando columna 'is_admin' a user...")
            cur.execute("""ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE;""")
            conn.commit()

        # ----------------------------
        # 3) rutina.tipo
        # ----------------------------
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='rutina' AND column_name='tipo';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando columna 'tipo' a rutina...")
            cur.execute("""ALTER TABLE rutina ADD COLUMN tipo VARCHAR(100) DEFAULT 'General';""")
            conn.commit()

        # ----------------------------
        # 4) rutina_item.ejercicio_id (por si falta)
        # ----------------------------
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='rutina_item' AND column_name='ejercicio_id';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando columna 'ejercicio_id' a rutina_item...")
            cur.execute("""ALTER TABLE rutina_item ADD COLUMN ejercicio_id INTEGER;""")
            conn.commit()

        # FK ejercicio_id (si no existe)
        cur.execute("""
            SELECT 1
            FROM information_schema.table_constraints
            WHERE constraint_type='FOREIGN KEY'
              AND table_name='rutina_item'
              AND constraint_name='rutina_item_ejercicio_id_fkey';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando FK rutina_item.ejercicio_id -> ejercicio.id ...")
            cur.execute("""
                ALTER TABLE rutina_item
                ADD CONSTRAINT rutina_item_ejercicio_id_fkey
                FOREIGN KEY (ejercicio_id) REFERENCES ejercicio(id);
            """)
            conn.commit()

        # ----------------------------
        # 5) Tabla athlete_check (si no existe)
        # ----------------------------
        cur.execute("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name='athlete_check';
        """)
        if not cur.fetchone():
            print("🛠️ Creando tabla athlete_check...")
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

        # ----------------------------
        # 6) Tabla athlete_log (si no existe)
        #    (para warmup_done/main_done/finisher_done + did_train)
        # ----------------------------
        cur.execute("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name='athlete_log';
        """)
        if not cur.fetchone():
            print("🛠️ Creando tabla athlete_log...")
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

        print("✅ Estructura de base sincronizada.")
        cur.close()
        conn.close()

    except Exception as e:
        print("⚠️ Error verificando estructura:", e)

ensure_columns()

# --- Crear admin si no existe ---
with app.app_context():
    db.create_all()

    admin = User.query.filter_by(email="admin@vir.app").first()
    if not admin:
        admin = User(
            nombre="Admin",
            email="admin@vir.app",
            grupo="Entrenador",
            is_admin=True
        )
        admin.set_password("V!ru_Admin-2025$X9")
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin creado correctamente.")
    else:
        # asegurar flag en True
        try:
            if getattr(admin, "is_admin", False) is False:
                admin.is_admin = True
                db.session.commit()
        except Exception:
            db.session.rollback()
        print("✅ Admin ya existe.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
