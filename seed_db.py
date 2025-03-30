from app.extensions import db
from app.models import Atleta, Entrenamiento
from app import create_app
from datetime import datetime

app = create_app()

with app.app_context():
    # Limpiar por si ya había datos
    Entrenamiento.query.delete()
    Atleta.query.delete()

    # Crear atletas
    atleta1 = Atleta(nombre='Juan Pérez', email='juan@example.com', edad=28, telefono='600123456')
    atleta2 = Atleta(nombre='Ana López', email='ana@example.com', edad=24, telefono='600654321')

    db.session.add_all([atleta1, atleta2])
    db.session.commit()

    # Crear entrenamientos
    entreno1 = Entrenamiento(
        atleta_id=atleta1.id,
        fecha=datetime(2025, 3, 25),
        dia='Martes',
        tipo='Fuerza',
        detalle='3x10 Sentadilla + Peso muerto'
    )

    entreno2 = Entrenamiento(
        atleta_id=atleta2.id,
        fecha=datetime(2025, 3, 25),
        dia='Martes',
        tipo='Series en pista',
        detalle='5x800m r2\''
    )

    db.session.add_all([entreno1, entreno2])
    db.session.commit()

    print("✅ Datos de prueba insertados correctamente.")
