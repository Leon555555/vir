from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
from app import create_app
from app.extensions import db

app = create_app()

# CREA LAS TABLAS si no existen (usado solo una vez)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run()
