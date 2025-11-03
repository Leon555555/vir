from app import create_app, db
from app.models import User
from datetime import datetime
import psycopg2, os

app = create_app()

def ensure_columns():
    """Verifica columnas críticas y las crea si faltan."""
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL no configurada.")
        return
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        # --- Verificar columna fecha_creacion en user ---
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='user' AND column_name='fecha_creacion';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando columna 'fecha_creacion' a user...")
            cur.execute("""ALTER TABLE "user" ADD COLUMN fecha_creacion TIMESTAMP DEFAULT NOW();""")
            conn.commit()

        # --- Verificar columna tipo en rutina ---
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='rutina' AND column_name='tipo';
        """)
        if not cur.fetchone():
            print("🛠️ Agregando columna 'tipo' a rutina...")
            cur.execute("""ALTER TABLE rutina ADD COLUMN tipo VARCHAR(100) DEFAULT 'General';""")
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
    if not User.query.filter_by(email="admin@vir.app").first():
        admin = User(
            nombre="Admin",
            email="admin@vir.app",
            grupo="Entrenador"
        )
        admin.set_password("V!ru_Admin-2025$X9")
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin creado correctamente.")
    else:
        print("✅ Admin ya existe.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
