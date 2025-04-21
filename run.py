# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    from flask_migrate import upgrade
    with app.app_context():
        upgrade()  # Solo se ejecuta si corres localmente: python run.py
    app.run(debug=True)
