from app import create_app
from app.models import db, Atleta

app = create_app()

with app.app_context():
    leandro = Atleta.query.filter_by(nombre="Leandro Videla").first()
    lucas = Atleta.query.filter_by(nombre="Lucas Alonso Duró").first()

    if leandro:
        leandro.email = "leandro@gmail.com"
        leandro.password = "lean123"
    else:
        print("❌ Leandro no existe")

    if lucas:
        lucas.email = "lucas@gmail.com"
        lucas.password = "lucas123"
    else:
        print("❌ Lucas no existe")

    db.session.commit()
    print("✅ Accesos asignados a Leandro y Lucas.")
