from app import create_app
from app.models import db, Atleta

app = create_app()

nombres = [
    "Leandro Videla",
    "Lucas Alonso Duró",
    "Guillaume Dubos",
    "Federico Civitillo",
    "Davis Sivilla",
    "Jordi Marti",
    "Guido Mure"
]

with app.app_context():
    for nombre in nombres:
        existe = Atleta.query.filter_by(nombre=nombre).first()
        if not existe:
            nuevo = Atleta(nombre=nombre)
            db.session.add(nuevo)
    db.session.commit()
    print("✅ Atletas agregados a la base de datos.")
