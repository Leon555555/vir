from app import create_app, db

app = create_app()

# Solo ejecuta esto si estás seguro que la DB está lista
with app.app_context():
    db.create_all()
