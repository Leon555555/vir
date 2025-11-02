from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.extensions import db

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.email == "viru@vir.app":
            return redirect(url_for("main.dashboard_entrenador"))
        else:
            return redirect(url_for("main.perfil_usuario", user_id=current_user.id))
    return redirect(url_for("main.login"))


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Bienvenido {user.nombre} 👋", "success")
            if user.email == "viru@vir.app":
                return redirect(url_for("main.dashboard_entrenador"))
            else:
                return redirect(url_for("main.perfil_usuario", user_id=user.id))
        else:
            flash("❌ Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        email = request.form.get("email")
        password = request.form.get("password")

        if not (nombre and email and password):
            flash("Por favor completa todos los campos", "danger")
            return redirect(url_for("main.register"))

        if User.query.filter_by(email=email).first():
            flash("Ese correo ya está registrado", "danger")
            return redirect(url_for("main.register"))

        nuevo = User(nombre=nombre, email=email)
        nuevo.set_password(password)
        db.session.add(nuevo)
        db.session.commit()

        flash("Cuenta creada correctamente. Ahora inicia sesión.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


@main_bp.route("/perfil")
@login_required
def perfil():
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))


@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id):
    if current_user.email == "viru@vir.app":
        user = User.query.get_or_404(user_id)
    else:
        if current_user.id != user_id:
            flash("Acceso denegado.", "danger")
            return redirect(url_for("main.perfil"))
        user = current_user
    return render_template("perfil.html", user=user)


@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if current_user.email != "viru@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    atletas = User.query.filter(User.email != "viru@vir.app").all()
    return render_template("dashboard_entrenador.html", atletas=atletas)


@main_bp.route("/coach/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_atleta():
    if current_user.email != "viru@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        password = request.form["password"]
        grupo = request.form.get("grupo")
        calendario_url = request.form.get("calendario_url")

        atleta = User(nombre=nombre, email=email, grupo=grupo, calendario_url=calendario_url)
        atleta.set_password(password)
        db.session.add(atleta)
        db.session.commit()

        flash(f"✅ Atleta '{nombre}' creado correctamente.", "success")
        return redirect(url_for("main.dashboard_entrenador"))

    return render_template("nuevo_atleta.html")


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("main.login"))
