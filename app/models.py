from .extensions import db
from datetime import datetime

class Atleta(db.Model):
    __tablename__ = 'atletas'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100))
    edad = db.Column(db.Integer)
    altura = db.Column(db.Float)
    peso = db.Column(db.Float)
    email = db.Column(db.String(120), unique=True)
    telefono = db.Column(db.String(20))
    foto_url = db.Column(db.String(255))  # URL o ruta a la foto

    # Tiempos personales
    test_1000 = db.Column(db.String(20))
    pr_10k = db.Column(db.String(20))
    pr_21k = db.Column(db.String(20))
    pr_42k = db.Column(db.String(20))

    entrenamientos = db.relationship('Entrenamiento', backref='atleta', lazy=True)
    
    def __repr__(self):
        return f'<Atleta {self.nombre}>'

class Entrenamiento(db.Model):
    __tablename__ = 'entrenamientos'

    id = db.Column(db.Integer, primary_key=True)
    atleta_id = db.Column(db.Integer, db.ForeignKey('atletas.id'), nullable=False)
    fecha = db.Column(db.Date)
    dia = db.Column(db.String(20))
    tipo = db.Column(db.String(50))
    detalle = db.Column(db.Text)

    def __repr__(self):
        return f'<Entrenamiento {self.tipo} - {self.fecha}>'

# app/models.py
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class Coach(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
