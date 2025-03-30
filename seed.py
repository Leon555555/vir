from app import create_app
from app.models import db, Coach
import os

# Crear app y contexto
app = create_app()

# 🚨 Añadir manualmente la URI si no está en el entorno
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'postgresql://urbanuser:RGjqKILxBrzidXLYMGWAf379GPm778tF@dpg-cvkjtfbuibrs73a26p40-a.oregon-postgres.render.com/urban_athletics'

# Reemplazá con tu URI de Render
# Por ejemplo:
# 'postgresql://urbanuser:RGjqKILxBrzidXLYMGWAf379GPm778tF@dpg-cvkjtfbuibrs73a26p40-a.oregon-postgres.render.com/urban_athletics'

db.init_app(app)
app.app_context().push()

# Crear el coach si no existe
if not Coach.query.filter_by(email="admin@urban.com").first():
    coach = Coach(email="admin@urban.com")
    coach.set_password("1234")
    db.session.add(coach)
    db.session.commit()
    print("✅ Coach creado con éxito.")
else:
    print("⚠️ Ya existe un coach con ese email.")
