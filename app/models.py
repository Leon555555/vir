from datetime import datetime, date as date_type

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

    # (si querés is_admin por rol, lo agregamos luego sin romper nada)
    # is_admin = db.Column(db.Boolean, default=False)

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

    # Video guardado (vos lo estás guardando en /static/videos/)
    video_filename = db.Column(db.String(255), nullable=False)

    # Opcional: miniatura
    imagen_filename = db.Column(db.String(255))

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    rutina_items = db.relationship(
        "RutinaItem",
        back_populates="ejercicio"
    )


# ===================================
# 🏋️‍♀️ Ejercicio dentro de una Rutina
# ===================================
class RutinaItem(db.Model):
    __tablename__ = "rutina_item"

    id = db.Column(db.Integer, primary_key=True)
    rutina_id = db.Column(db.Integer, db.ForeignKey("rutina.id"), nullable=False)

    # link al banco de ejercicios
    ejercicio_id = db.Column(db.Integer, db.ForeignKey("ejercicio.id"))

    nombre = db.Column(db.String(200), nullable=False)
    series = db.Column(db.String(50))
    reps = db.Column(db.String(50))
    descanso = db.Column(db.String(50))
    imagen_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))

    # ✅ OJO: se llama NOTA (no "notas")
    nota = db.Column(db.Text)

    ejercicio = db.relationship(
        "Ejercicio",
        back_populates="rutina_items"
    )


# ===================================
# 📅 Modelo de día planificado (propuesto por coach)
# ===================================
class DiaPlan(db.Model):
    __tablename__ = "dia_plan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    # tipo del día (descanso / run / fuerza / etc.)
    plan_type = db.Column(db.String(50), default="descanso")

    # propuesto por el entrenador
    warmup = db.Column(db.Text)
    main = db.Column(db.Text)
    finisher = db.Column(db.Text)

    # scores
    propuesto_score = db.Column(db.Integer, default=0)
    realizado_score = db.Column(db.Integer, default=0)

    # atleta (feedback / disponibilidad)
    puede_entrenar = db.Column(db.String(50))
    dificultad = db.Column(db.String(50))
    comentario_atleta = db.Column(db.Text)

    user = db.relationship("User", backref="dias", lazy=True)


# ===================================
# ✅ Check por ejercicio (per-item) (persistente)
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
        db.UniqueConstraint("user_id", "fecha", "rutina_item_id", name="uq_check_user_fecha_item"),
    )


# ===================================
# ✅ Registro de lo REALIZADO (sin tocar lo propuesto)
#   - el atleta puede escribir qué hizo (warmup/main/finisher)
#   - marcar si realizó el entreno
#   - esto alimenta "Progreso" después
# ===================================
class AthleteDayResult(db.Model):
    __tablename__ = "athlete_day_result"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    # ¿lo completó?
    did_workout = db.Column(db.Boolean, default=False, nullable=False)

    # lo que hizo realmente (editable por atleta)
    warmup_done = db.Column(db.Text)
    main_done = db.Column(db.Text)
    finisher_done = db.Column(db.Text)

    # opcional: comentario / sensaciones
    notes = db.Column(db.Text)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "fecha", name="uq_result_user_fecha"),
    )
