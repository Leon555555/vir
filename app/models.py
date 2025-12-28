# app/models.py
from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    grupo = db.Column(db.String(80), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Flask-Login
    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def strava_account(self):
        return IntegrationAccount.query.filter_by(user_id=self.id, provider="strava").first()


class DiaPlan(db.Model):
    __tablename__ = "dia_plan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False, index=True)

    # legacy
    plan_type = db.Column(db.String(40), default="Descanso", nullable=False)
    warmup = db.Column(db.Text, default="", nullable=False)
    main = db.Column(db.Text, default="", nullable=False)
    finisher = db.Column(db.Text, default="", nullable=False)

    puede_entrenar = db.Column(db.String(5), default="si", nullable=False)  # si/no
    comentario_atleta = db.Column(db.String(200), default="", nullable=False)

    propuesto_score = db.Column(db.Integer, default=0, nullable=False)

    # ✅ NUEVO: bloques del día (para tabata + run + ejercicios sueltos etc)
    blocks = db.Column(JSONB, default=list, nullable=False)

    user = db.relationship("User", backref=db.backref("planes", lazy=True))

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", name="uq_dia_plan_user_fecha"),
    )


class Rutina(db.Model):
    __tablename__ = "rutinas"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(140), nullable=False)
    tipo = db.Column(db.String(60), default="", nullable=False)
    descripcion = db.Column(db.Text, default="", nullable=False)

    created_by = db.Column(db.Integer, nullable=True)

    # Si existe -> rutina se puede usar como Tabata
    tabata_preset = db.Column(JSONB, nullable=True)

    items = db.relationship("RutinaItem", backref="rutina", lazy=True, cascade="all, delete-orphan")


class Ejercicio(db.Model):
    __tablename__ = "ejercicios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(140), nullable=False)
    categoria = db.Column(db.String(120), default="", nullable=False)
    descripcion = db.Column(db.Text, default="", nullable=False)

    video_filename = db.Column(db.String(255), default="", nullable=False)


class RutinaItem(db.Model):
    __tablename__ = "rutina_items"

    id = db.Column(db.Integer, primary_key=True)
    rutina_id = db.Column(db.Integer, db.ForeignKey("rutinas.id"), nullable=False, index=True)
    ejercicio_id = db.Column(db.Integer, db.ForeignKey("ejercicios.id"), nullable=True, index=True)

    nombre = db.Column(db.String(140), nullable=False)

    series = db.Column(db.String(40), nullable=True)
    reps = db.Column(db.String(40), nullable=True)
    peso = db.Column(db.String(40), nullable=True)
    descanso = db.Column(db.String(40), nullable=True)
    nota = db.Column(db.Text, nullable=True)

    posicion = db.Column(db.Integer, default=0, nullable=False)

    # opcional: si algún item apunta a un video fuera del banco
    video_url = db.Column(db.String(255), nullable=True)

    ejercicio = db.relationship("Ejercicio", backref=db.backref("rutina_items", lazy=True))


class AthleteLog(db.Model):
    __tablename__ = "athlete_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False, index=True)

    did_train = db.Column(db.Boolean, default=False, nullable=False)

    warmup_done = db.Column(db.Text, default="", nullable=False)
    main_done = db.Column(db.Text, default="", nullable=False)
    finisher_done = db.Column(db.Text, default="", nullable=False)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", name="uq_athlete_logs_user_fecha"),
    )


class AthleteCheck(db.Model):
    __tablename__ = "athlete_checks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    fecha = db.Column(db.Date, nullable=False, index=True)

    rutina_item_id = db.Column(db.Integer, db.ForeignKey("rutina_items.id"), nullable=False, index=True)
    done = db.Column(db.Boolean, default=False, nullable=False)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", "rutina_item_id", name="uq_athlete_checks_unique"),
    )


class IntegrationAccount(db.Model):
    __tablename__ = "integration_accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    provider = db.Column(db.String(40), nullable=False)  # "strava"
    access_token = db.Column(db.String(255), nullable=True)
    refresh_token = db.Column(db.String(255), nullable=True)
    expires_at = db.Column(db.Integer, nullable=True)

    external_user_id = db.Column(db.String(80), nullable=True)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "provider", name="uq_integration_accounts_user_provider"),
    )
