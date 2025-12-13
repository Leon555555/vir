from __future__ import annotations

from datetime import datetime, date
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
    is_admin = db.Column(db.Boolean, default=False)  # <-- IMPORTANTE
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

    # archivo en /static/videos (o /static/videos_ejercicios si lo usás así)
    video_filename = db.Column(db.String(255), nullable=False)
    imagen_filename = db.Column(db.String(255))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    rutina_items = db.relationship("RutinaItem", back_populates="ejercicio")


# ===================================
# 🏋️‍♀️ Ejercicio dentro de una Rutina
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

    # ✅ ESTE ES EL NOMBRE REAL DEL CAMPO:
    nota = db.Column(db.Text)

    ejercicio = db.relationship("Ejercicio", back_populates="rutina_items")


# ===================================
# 📅 Plan del día
# ===================================
class DiaPlan(db.Model):
    __tablename__ = "dia_plan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    plan_type = db.Column(db.String(50), default="descanso")  # fuerza / run / etc
    warmup = db.Column(db.Text)
    main = db.Column(db.Text)       # puede ser texto o "RUTINA:<id>"
    finisher = db.Column(db.Text)

    propuesto_score = db.Column(db.Integer, default=0)
    realizado_score = db.Column(db.Integer, default=0)

    # “calendario”: si puede entrenar o no
    puede_entrenar = db.Column(db.String(50))  # "si" / "no"
    dificultad = db.Column(db.String(50))
    comentario_atleta = db.Column(db.Text)

    user = db.relationship("User", backref="dias", lazy=True)


# ===================================
# ✅ Check por ejercicio (fuerza) persistente
# ===================================
class AthleteCheck(db.Model):
    __tablename__ = "athlete_check"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    rutina_item_id = db.Column(db.Integer, db.ForeignKey("rutina_item.id"), nullable=False)
    done = db.Column(db.Boolean, default=True, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", "rutina_item_id", name="uq_athlete_check"),
    )


# ===================================
# ✅ Registro "lo realizado" (no pisa lo del coach)
#    Sirve para run/bike/etc (warmup/main/finisher) + confirmación
# ===================================
class AthleteLog(db.Model):
    __tablename__ = "athlete_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    did_train = db.Column(db.Boolean, default=False, nullable=False)

    warmup_done = db.Column(db.Text)
    main_done = db.Column(db.Text)
    finisher_done = db.Column(db.Text)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", name="uq_athlete_log"),
    )
