# app/routes/auth.py
from __future__ import annotations

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.models import User
from . import main_bp, is_admin


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if is_admin():
            return redirect(url_for("main.dashboard_entrenador"))
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))
    return redirect(url_for("main.login"))


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Bienvenido {user.nombre}", "success")

            nxt = request.args.get("next")
            if nxt:
                return redirect(nxt)

            if is_admin():
                return redirect(url_for("main.dashboard_entrenador"))
            return redirect(url_for("main.perfil_usuario", user_id=user.id))

        flash("Datos incorrectos", "danger")

    return render_template("login.html")


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada", "info")
    return redirect(url_for("main.login"))


@main_bp.route("/perfil")
@login_required
def perfil_redirect():
    if is_admin():
        return redirect(url_for("main.dashboard_entrenador"))
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))
