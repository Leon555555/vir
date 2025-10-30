from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    __tablename__ = "users"  # plural y más estándar

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    grupo = db.Column(db.String(50))
    calendario_url = db.Column(db.String(255))
    foto = db.Column(db.String(255))  # opcional para perfil o avatar futuro

    # =============================
    # 🔐 MÉTODOS DE AUTENTICACIÓN
    # =============================
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.nombre} ({self.email})>"
class Sesion(db.Model):
    __tablename__ = "sesiones"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(255))
    duracion = db.Column(db.Integer)  # en minutos
    intensidad = db.Column(db.String(50))

    user = db.relationship("User", backref=db.backref("sesiones", lazy=True))

    def __repr__(self):
        return f"<Sesion {self.tipo} - {self.fecha}>"
