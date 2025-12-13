from __future__ import annotations

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

    # ✅ Arquitectura pro: rol admin persistente
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


# ===================================
# 🧱 Modelo de Rutina
# ===================================
class Rutina(db.Model):
    __tablename__ = "rutina"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(db.String(100), default="General")
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship(
        "RutinaItem",
        backref="rutina",
        cascade="all, delete-orphan",
        order_by="RutinaItem.id",
    )


# ===================================
# 🎥 Banco de Ejercicios
# ===================================
class Ejercicio(db.Model):
    __tablename__ = "ejercicio"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(50))
    descripcion = db.Column(db.Text)

    # nombre del archivo mp4 en /static/videos_ejercicios/
    video_filename = db.Column(db.String(255), nullable=False)

    imagen_filename = db.Column(db.String(255))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    rutina_items = db.relationship(
        "RutinaItem",
        back_populates="ejercicio",
    )


# ===================================
# 🏋️‍♀️ Ejercicio dentro de una Rutina (RutinaItem)
# ===================================
class RutinaItem(db.Model):
    __tablename__ = "rutina_item"

    id = db.Column(db.Integer, primary_key=True)
    rutina_id = db.Column(db.Integer, db.ForeignKey("rutina.id"), nullable=False)

    ejercicio_id = db.Column(db.Integer, db.ForeignKey("ejercicio.id"))

    nombre = db.Column(db.String(200), nullable=False)
    series = db.Column(db.String(50))
    reps = db.Column(db.String(50))
    descanso = db.Column(db.String(50))

    imagen_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))

    # ✅ campo canonical
    nota = db.Column(db.Text)

    # ✅ compatibilidad: tu template / routes a veces usan "notas"
    @property
    def notas(self):
        return self.nota

    @notas.setter
    def notas(self, value):
        self.nota = value

    ejercicio = db.relationship(
        "Ejercicio",
        back_populates="rutina_items",
    )


# ===================================
# 📅 Modelo de día planificado
# ===================================
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

    # feedback atleta
    puede_entrenar = db.Column(db.String(50))
    dificultad = db.Column(db.String(50))
    comentario_atleta = db.Column(db.Text)

    user = db.relationship("User", backref="dias", lazy=True)


# ===================================
# ✅ Persistencia: checks por ejercicio/día del atleta
# ===================================
class AthleteCheck(db.Model):
    __tablename__ = "athlete_check"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    rutina_item_id = db.Column(db.Integer, db.ForeignKey("rutina_item.id", ondelete="CASCADE"), nullable=False)

    done = db.Column(db.Boolean, default=True, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", "rutina_item_id", name="uq_athlete_check"),
    )
