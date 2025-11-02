from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ---------- USUARIOS ----------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    grupo = db.Column(db.String(50))
    calendario_url = db.Column(db.String(255))
    foto = db.Column(db.String(255))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ---------- PLANES DIARIOS ----------
class DiaPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    plan_type = db.Column(db.String(30), default="descanso")
    warmup = db.Column(db.Text)
    main = db.Column(db.Text)
    finisher = db.Column(db.Text)
    propuesto_score = db.Column(db.Integer)
    realizado_score = db.Column(db.Integer)

# ---------- RUTINAS ----------
class Rutina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    items = db.relationship("RutinaItem", backref="rutina", cascade="all, delete-orphan", order_by="RutinaItem.orden")

class RutinaItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rutina_id = db.Column(db.Integer, db.ForeignKey("rutina.id"), nullable=False)
    orden = db.Column(db.Integer, default=0)
    nombre = db.Column(db.String(120), nullable=False)
    reps = db.Column(db.String(80))
    video_url = db.Column(db.String(255))
    imagen_url = db.Column(db.String(255))
    nota = db.Column(db.Text)
