# app/models.py
from __future__ import annotations

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    grupo = db.Column(db.String(120), nullable=True)

    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class DiaPlan(db.Model):
    __tablename__ = "dia_plan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    fecha = db.Column(db.Date, nullable=False, index=True)
    plan_type = db.Column(db.String(50), nullable=True, default="Descanso")

    warmup = db.Column(db.Text, nullable=True)
    main = db.Column(db.Text, nullable=True)
    finisher = db.Column(db.Text, nullable=True)

    propuesto_score = db.Column(db.Integer, nullable=True, default=0)
    realizado_score = db.Column(db.Integer, nullable=True, default=0)

    puede_entrenar = db.Column(db.String(10), nullable=True, default="si")
    comentario_atleta = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", name="uq_diaplan_user_fecha"),
    )


class AthleteLog(db.Model):
    __tablename__ = "athlete_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fecha = db.Column(db.Date, nullable=False, index=True)

    did_train = db.Column(db.Boolean, nullable=False, default=False)
    warmup_done = db.Column(db.Text, nullable=True)
    main_done = db.Column(db.Text, nullable=True)
    finisher_done = db.Column(db.Text, nullable=True)

    updated_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", name="uq_athletelog_user_fecha"),
    )


class AthleteCheck(db.Model):
    __tablename__ = "athlete_checks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fecha = db.Column(db.Date, nullable=False, index=True)

    rutina_item_id = db.Column(db.Integer, nullable=False, index=True)
    done = db.Column(db.Boolean, nullable=False, default=False)

    updated_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", "rutina_item_id", name="uq_check_user_fecha_item"),
    )


# -------------------------------------------------------------
# Rutinas / Ejercicios / Items
# -------------------------------------------------------------
class Rutina(db.Model):
    __tablename__ = "rutinas"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(60), nullable=True)
    descripcion = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.Integer, nullable=True)

    # Relación (no cambia DB, solo ORM)
    items = db.relationship(
        "RutinaItem",
        back_populates="rutina",
        lazy="select",
        order_by="RutinaItem.posicion.asc(), RutinaItem.id.asc()",
        cascade="all, delete-orphan",
    )


class Ejercicio(db.Model):
    __tablename__ = "ejercicios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(80), nullable=True)
    descripcion = db.Column(db.String(255), nullable=True)
    video_filename = db.Column(db.String(255), nullable=True)


class RutinaItem(db.Model):
    __tablename__ = "rutina_items"

    id = db.Column(db.Integer, primary_key=True)

    # ✅ IMPORTANTE: FK reales (no cambia tu arquitectura visual, solo consistencia)
    rutina_id = db.Column(
        db.Integer,
        db.ForeignKey("rutinas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ejercicio_id = db.Column(
        db.Integer,
        db.ForeignKey("ejercicios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    nombre = db.Column(db.String(120), nullable=False)

    # strings porque usas cosas como: "30\"", "1'", "8-10", etc.
    series = db.Column(db.String(40), nullable=True)
    reps = db.Column(db.String(40), nullable=True)

    # ✅ columnas que tu query está intentando leer
    peso = db.Column(db.String(40), nullable=True)

    descanso = db.Column(db.String(40), nullable=True)
    nota = db.Column(db.String(255), nullable=True)
    video_url = db.Column(db.String(255), nullable=True)

    # ✅ orden persistente
    posicion = db.Column(db.Integer, nullable=False, default=0, index=True)

    # Relaciones (no cambian DB)
    rutina = db.relationship("Rutina", back_populates="items", lazy="joined")
    ejercicio = db.relationship("Ejercicio", lazy="joined")
