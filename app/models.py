from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class Atleta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    telefono = db.Column(db.String(20))
    edad = db.Column(db.Integer)
    altura = db.Column(db.Float)
    peso = db.Column(db.Float)
    pr_1000m = db.Column(db.String(20))
    pr_10k = db.Column(db.String(20))
    pr_21k = db.Column(db.String(20))
    pr_42k = db.Column(db.String(20))
    entrenamientos = db.relationship('Entrenamiento', backref='atleta', lazy=True)

class Entrenamiento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    atleta_id = db.Column(db.Integer, db.ForeignKey('atleta.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    detalle = db.Column(db.Text)
    realizado = db.Column(db.Boolean, default=False)

class Coach(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
