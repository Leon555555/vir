# app/models.py
from __future__ import annotations

from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # roles simples (si usás admin/coach)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # relaciones
    rutinas = db.relationship("Rutina", backref="user", lazy=True)

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)


class DiaPlan(db.Model):
    """
    Opcional: un 'día' por atleta.
    Si ya tenés tu propio modelo, mantenelo.
    """
    __tablename__ = "dia_plan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)

    user = db.relationship("User", backref=db.backref("dias_plan", lazy=True))


class Rutina(db.Model):
    __tablename__ = "rutina"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # IMPORTANTE: en tu app puede llamarse "fecha" o "dia"
    fecha = db.Column(db.Date, nullable=False, index=True)

    nombre = db.Column(db.String(200), nullable=False, default="Rutina")
    notas = db.Column(db.Text, nullable=True)

    items = db.relationship(
        "RutinaItem",
        backref="rutina",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="RutinaItem.orden.asc()",
    )


class Ejercicio(db.Model):
    __tablename__ = "ejercicio"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(80), nullable=True)  # fuerza/run/etc

    # si guardás video/imagen:
    video_url = db.Column(db.String(500), nullable=True)
    imagen_url = db.Column(db.String(500), nullable=True)


class RutinaItem(db.Model):
    __tablename__ = "rutina_item"

    id = db.Column(db.Integer, primary_key=True)

    rutina_id = db.Column(db.Integer, db.ForeignKey("rutina.id"), nullable=False)

    ejercicio_id = db.Column(db.Integer, db.ForeignKey("ejercicio.id"), nullable=True)
    ejercicio = db.relationship("Ejercicio")

    # detalle
    orden = db.Column(db.Integer, default=0, nullable=False)
    series = db.Column(db.String(50), nullable=True)
    repeticiones = db.Column(db.String(50), nullable=True)
    peso = db.Column(db.String(50), nullable=True)
    descanso = db.Column(db.String(50), nullable=True)
    notas = db.Column(db.Text, nullable=True)

    # ✅ NUEVO: persistencia Hecho/Redo
    done = db.Column(db.Boolean, nullable=False, default=False)
    done_at = db.Column(db.DateTime, nullable=True)

    def mark_done(self) -> None:
        self.done = True
        self.done_at = datetime.utcnow()

    def mark_undone(self) -> None:
        self.done = False
        self.done_at = None
