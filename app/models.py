# app/models.py
from __future__ import annotations

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"  # ✅ IMPORTANTE: plural y estándar

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)

    grupo = db.Column(db.String(120), nullable=True)

    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class DiaPlan(db.Model):
    __tablename__ = "dia_plan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False, index=True)

    plan_type = db.Column(db.String(40), nullable=False, default="Descanso")

    warmup = db.Column(db.Text, nullable=True)
    main = db.Column(db.Text, nullable=True)
    finisher = db.Column(db.Text, nullable=True)

    propuesto_score = db.Column(db.Integer, nullable=True, default=0)
    realizado_score = db.Column(db.Integer, nullable=True, default=0)

    puede_entrenar = db.Column(db.String(10), nullable=True, default="si")
    comentario_atleta = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", name="uq_plan_user_fecha"),
    )


class Rutina(db.Model):
    __tablename__ = "rutina"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(180), nullable=False)
    tipo = db.Column(db.String(100), nullable=True, default="General")
    descripcion = db.Column(db.Text, nullable=True)

    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Ejercicio(db.Model):
    __tablename__ = "ejercicio"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(180), nullable=False)
    categoria = db.Column(db.String(120), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)

    video_filename = db.Column(db.String(255), nullable=True)


class RutinaItem(db.Model):
    __tablename__ = "rutina_item"

    id = db.Column(db.Integer, primary_key=True)
    rutina_id = db.Column(db.Integer, db.ForeignKey("rutina.id"), nullable=False, index=True)
    ejercicio_id = db.Column(db.Integer, db.ForeignKey("ejercicio.id"), nullable=True)

    nombre = db.Column(db.String(180), nullable=False)

    series = db.Column(db.String(50), nullable=True)
    reps = db.Column(db.String(50), nullable=True)
    descanso = db.Column(db.String(50), nullable=True)

    nota = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.String(255), nullable=True)


class AthleteCheck(db.Model):
    __tablename__ = "athlete_check"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False, index=True)
    rutina_item_id = db.Column(db.Integer, db.ForeignKey("rutina_item.id"), nullable=False, index=True)

    done = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", "rutina_item_id", name="uq_check_user_fecha_item"),
    )


class AthleteLog(db.Model):
    __tablename__ = "athlete_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False, index=True)

    did_train = db.Column(db.Boolean, nullable=False, default=False)

    warmup_done = db.Column(db.Text, nullable=True)
    main_done = db.Column(db.Text, nullable=True)
    finisher_done = db.Column(db.Text, nullable=True)

    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", name="uq_log_user_fecha"),
    )
