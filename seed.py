# seed.py
from app import create_app
from app.models import db, Atleta

app = create_app()

with app.app_context():
    atletas = [
        {"nombre": "Leandro Videla", "email": "lvidelaramos@gmail.com", "telefono": "111111111", "edad": 30, "altura": 175, "peso": 70},
        {"nombre": "Lucas Alonso Duró", "email": "lucas@example.com", "telefono": "222222222", "edad": 28, "altura": 178, "peso": 72},
        {"nombre": "Guillaume Dubos", "email": "guillaume@example.com"},
        {"nombre": "Federico Civitillo", "email": "fede@example.com"},
        {"nombre": "Davis Sivilla", "email": "davis@example.com"},
        {"nombre": "Jordi Marti", "email": "jordi@example.com"},
        {"nombre": "Guido Mure", "email": "guido@example.com"},
    ]

    for data in atletas:
        if not Atleta.query.filter_by(nombre=data["nombre"]).first():
            nuevo = Atleta(**data)
            db.session.add(nuevo)

    db.session.commit()
    print("✔ Atletas insertados correctamente.")
