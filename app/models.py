from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)       # antes 100
    email = db.Column(db.String(255), unique=True, nullable=False)  # antes 120
    password_hash = db.Column(db.Text, nullable=False)       # antes String(128)
    edad = db.Column(db.Integer)
    altura = db.Column(db.Float)
    peso = db.Column(db.Float)
    grupo = db.Column(db.String(100))                        # antes 50
    foto = db.Column(db.Text)                                # antes String(255)

    def set_password(self, password):
        """Genera y guarda un hash seguro para la contraseña."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica si la contraseña es correcta."""
        return check_password_hash(self.password_hash, password)
