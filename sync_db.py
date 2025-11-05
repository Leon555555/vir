import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

cur.execute("""
ALTER TABLE rutina ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
""")

conn.commit()
cur.close()
conn.close()
print("✅ Columna 'fecha_creacion' creada correctamente en la tabla rutina.")
