from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    grupo = db.Column(db.String(50))
    calendario_url = db.Column(db.String(255))
    foto = db.Column(db.String(255))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ====== Planificación diaria del atleta ======
# plan_type: fuerza|correr|natacion|descanso|fisioterapia|bike
class DiaPlan(db.Model):
    __tablename__ = "dia_plan"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    plan_type = db.Column(db.String(20), nullable=False, default="descanso")

    warmup = db.Column(db.Text)        # Calentamiento
    main = db.Column(db.Text)          # Entrenamiento principal
    finisher = db.Column(db.Text)      # Bloque final

    propuesto_score = db.Column(db.Integer, default=0)  # p.ej. minutos/volumen propuesto
    realizado_score = db.Column(db.Integer, default=0)  # p.ej. minutos/volumen realizado

    user = db.relationship("User", backref=db.backref("planes", lazy=True))


# ====== Rutinas de Fuerza (catálogo) ======
class Rutina(db.Model):
    __tablename__ = "rutina"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    nivel = db.Column(db.String(30), default="General")  # Principiante / Intermedio / Avanzado
    duracion_min = db.Column(db.Integer, default=45)
    imagen_url = db.Column(db.String(255))
    descripcion = db.Column(db.Text)

    # relación ejercicios
    ejercicios = db.relationship("RutinaItem", backref="rutina", cascade="all, delete-orphan")


class RutinaItem(db.Model):
    __tablename__ = "rutina_item"

    id = db.Column(db.Integer, primary_key=True)
    rutina_id = db.Column(db.Integer, db.ForeignKey("rutina.id"), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    series = db.Column(db.Integer, default=3)
    repeticiones = db.Column(db.String(50), default="8-12")
    video_url = db.Column(db.String(255))  # link a video (YouTube, Drive, etc.)
