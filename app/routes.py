from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.extensions import db

main_bp = Blueprint("main", __name__)

# Página principal
@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.perfil"))
    return redirect(url_for("main.login"))

# Login
@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("main.perfil"))
        else:
            flash("Usuario o contraseña incorrectos", "danger")
    return render_template("login.html")

# Registro
@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("Ya existe un usuario con ese email.")
            return redirect(url_for("main.register"))

        nuevo = User(nombre=nombre, email=email)
        nuevo.set_password(password)
        db.session.add(nuevo)
        db.session.commit()
        flash("Usuario creado correctamente. Ahora puedes iniciar sesión.")
        return redirect(url_for("main.login"))

    return render_template("register.html")

# Perfil
@main_bp.route("/perfil")
@login_required
def perfil():
    return render_template("perfil.html", user=current_user)

# Logout
@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.")
    return redirect(url_for("main.login"))
