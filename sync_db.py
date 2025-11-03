import psycopg2
import os

# Usa tu misma URL de Render (copiala desde tu __init__.py)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://vir_db_user:bRbsLtpZ3I4rag19scmcAfRyXjZVNsUw@dpg-d3vtoc75r7bs73ch4bc0-a/vir_db"
)

def ensure_fecha_creacion():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    # Verificar si la columna existe
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='user' AND column_name='fecha_creacion';
    """)
    result = cur.fetchone()

    if not result:
        print("🛠️ Agregando columna 'fecha_creacion' a la tabla user...")
        cur.execute("""
            ALTER TABLE "user" ADD COLUMN fecha_creacion TIMESTAMP DEFAULT NOW();
        """)
        conn.commit()
        print("✅ Columna agregada correctamente.")
    else:
        print("✅ La columna 'fecha_creacion' ya existe, no se hace nada.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    ensure_fecha_creacion()
