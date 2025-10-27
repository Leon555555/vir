from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Coach
from app.extensions import db

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home():
    if "user_email" in session:
        return redirect(url_for("main.perfil"))
    return redirect(url_for("main.login"))

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = Coach.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_email"] = user.email
            return redirect(url_for("main.perfil"))
        flash("Usuario o contraseña incorrectos", "danger")
    return render_template("login.html")

@main_bp.route("/perfil")
def perfil():
    if "user_email" not in session:
        flash("Inicia sesión primero.", "warning")
        return redirect(url_for("main.login"))

    user = Coach.query.filter_by(email=session["user_email"]).first()

    saludo_base = user.apodo or user.nombre or user.email
    saludo = f"Bienvenida, {saludo_base} 💫" if saludo_base else "Bienvenido/a 💫"

    return render_template("perfil.html", user=user, saludo=saludo)

@main_bp.route("/logout")
def logout():
    session.pop("user_email", None)
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("main.login"))
