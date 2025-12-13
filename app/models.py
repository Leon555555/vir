from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db

# ===================================
# 👤 Modelo de usuario
# ===================================
class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    grupo = db.Column(db.String(50), default="Atleta")
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ===================================
# 🧱 Modelo de Rutina
# ===================================
class Rutina(db.Model):
    __tablename__ = "rutina"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(db.String(100), default="General")  # fuerza, pista, bike, etc.
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship(
        "RutinaItem",
        backref="rutina",
        cascade="all, delete-orphan",
        order_by="RutinaItem.id"
    )


# ===================================
# 🎥 Banco de Ejercicios
# ===================================
class Ejercicio(db.Model):
    __tablename__ = "ejercicio"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(50))  # fuerza, core, movilidad, etc.
    descripcion = db.Column(db.Text)

    # Nombre del archivo de vídeo guardado en /static/videos_ejercicios
    video_filename = db.Column(db.String(255), nullable=False)

    # Opccional: miniatura
    imagen_filename = db.Column(db.String(255))

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Items de rutina que usan este ejercicio
    rutina_items = db.relationship(
        "RutinaItem",
        back_populates="ejercicio"
    )


# ===================================
# 🏋️‍♀️ Ejercicio dentro de una Rutina (RutinaItem)
# ===================================
class RutinaItem(db.Model):
    __tablename__ = "rutina_item"

    id = db.Column(db.Integer, primary_key=True)
    rutina_id = db.Column(db.Integer, db.ForeignKey("rutina.id"), nullable=False)

    # Opcional: link al banco de ejercicios
    ejercicio_id = db.Column(db.Integer, db.ForeignKey("ejercicio.id"))

    # Campos que ya usabas
    nombre = db.Column(db.String(200), nullable=False)
    series = db.Column(db.String(50))
    reps = db.Column(db.String(50))
    descanso = db.Column(db.String(50))
    imagen_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    nota = db.Column(db.Text)

    # ✅ NUEVO: persistencia Hecho / Redo
    done = db.Column(db.Boolean, nullable=False, default=False)
    done_at = db.Column(db.DateTime, nullable=True)

    ejercicio = db.relationship(
        "Ejercicio",
        back_populates="rutina_items"
    )


# ===================================
# 📅 Modelo de día planificado
# ===================================
class DiaPlan(db.Model):
    __tablename__ = "dia_plan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    # ✅ NUEVO: asignar una rutina a un día (para moverla entre días)
    rutina_id = db.Column(db.Integer, db.ForeignKey("rutina.id"), nullable=True)
    rutina = db.relationship("Rutina", lazy=True)

    plan_type = db.Column(db.String(50), default="descanso")
    warmup = db.Column(db.Text)
    main = db.Column(db.Text)
    finisher = db.Column(db.Text)
    propuesto_score = db.Column(db.Integer, default=0)
    realizado_score = db.Column(db.Integer, default=0)

    # Campos que usa serialize_plan en routes.py
    puede_entrenar = db.Column(db.String(50))
    dificultad = db.Column(db.String(50))
    comentario_atleta = db.Column(db.Text)

    user = db.relationship("User", backref="dias", lazy=True)
