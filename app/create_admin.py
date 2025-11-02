# create_admin.py
from app import create_app
from app.extensions import db
from app.models import User

APP = create_app()
with APP.app_context():
    email = "viru@vir.app"
    nombre = "Viru"
    password = "TuPassFuerte123!"  # Cambialo por la contraseña que quieras

    user = User.query.filter_by(email=email).first()
    if user:
        print("Usuario ya existe. Actualizando contraseña...")
        user.set_password(password)
    else:
        print("Creando usuario admin Viru...")
        user = User(nombre=nombre, email=email)
        user.set_password(password)
        db.session.add(user)

    db.session.commit()
    print("Hecho. Admin listo. Email:", email)
