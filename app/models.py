from datetime import datetime
from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


# ===========================
# 👤 MODELO USER
# ===========================
class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    grupo = db.Column(db.String(50), default="Atleta")
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)  # ✅ Campo nuevo agregado correctamente

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ===========================
# 📅 MODELO DIA PLAN
# ===========================
class DiaPlan(db.Model):
    __tablename__ = "diaplan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    plan_type = db.Column(db.String(50), default="descanso")
    warmup = db.Column(db.Text)
    main = db.Column(db.Text)
    finisher = db.Column(db.Text)
    propuesto_score = db.Column(db.Integer, default=0)
    realizado_score = db.Column(db.Integer, default=0)

    user = db.relationship("User", backref=db.backref("dias", cascade="all, delete-orphan"))


# ===========================
# 💪 MODELO RUTINA
# ===========================
class Rutina(db.Model):
    __tablename__ = "rutina"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(db.String(50), default="Fuerza")  # ✅ Tipo agregado correctamente
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("Ejercicio", backref="rutina", cascade="all, delete-orphan")


# ===========================
# 🏋️‍♀️ MODELO EJERCICIO
# ===========================
class Ejercicio(db.Model):
    __tablename__ = "ejercicio"

    id = db.Column(db.Integer, primary_key=True)
    rutina_id = db.Column(db.Integer, db.ForeignKey("rutina.id"), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    series = db.Column(db.String(20))
    reps = db.Column(db.String(20))
    descanso = db.Column(db.String(50))
    imagen_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    nota = db.Column(db.Text)
