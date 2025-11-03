from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

# =======================================
# 👤 Modelo Usuario
# =======================================
class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    grupo = db.Column(db.String(80))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación con los días de entrenamiento
    dias_plan = db.relationship("DiaPlan", backref="usuario", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.nombre}>"


# =======================================
# 📅 Modelo Día de plan
# =======================================
class DiaPlan(db.Model):
    __tablename__ = "dia_plan"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    plan_type = db.Column(db.String(50), default="descanso")
    warmup = db.Column(db.Text)
    main = db.Column(db.Text)
    finisher = db.Column(db.Text)
    propuesto_score = db.Column(db.Integer, default=0)
    realizado_score = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<DiaPlan {self.fecha} {self.plan_type}>"


# =======================================
# 🏋️ Modelo Rutina
# =======================================
class Rutina(db.Model):
    __tablename__ = "rutina"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(db.String(50), default="Fuerza")  # 👈 tipo de rutina (Fuerza, Estiramientos, Movilidad)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))  # quién la creó

    # Relación con ejercicios
    items = db.relationship("RutinaItem", backref="rutina", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Rutina {self.nombre} ({self.tipo})>"


# =======================================
# 🧩 Modelo Ejercicios dentro de una rutina
# =======================================
class RutinaItem(db.Model):
    __tablename__ = "rutina_item"
    id = db.Column(db.Integer, primary_key=True)
    rutina_id = db.Column(db.Integer, db.ForeignKey("rutina.id"), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    reps = db.Column(db.String(50))
    series = db.Column(db.String(50))
    descanso = db.Column(db.String(50))
    imagen_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    nota = db.Column(db.Text)

    def __repr__(self):
        return f"<Ejercicio {self.nombre}>"
