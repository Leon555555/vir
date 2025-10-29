from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.extensions import db
from . import main_bp

# ======================================
# LOGIN Y PERFIL
# ======================================

@main_bp.route("/")
def index():
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
                return redirect(url_for("main.perfil"))
        else:
            flash("❌ Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")

@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("main.login"))

@main_bp.route("/perfil")
@login_required
def perfil():
    return render_template("perfil.html", user=current_user)

# ======================================
# DASHBOARD DEL ENTRENADOR
# ======================================

@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if current_user.email != "viru@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    atletas = User.query.filter(User.email != "viru@vir.app").all()
    return render_template("dashboard_entrenador.html", atletas=atletas)

# ======================================
# CREAR NUEVO ATLETA
# ======================================

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

# ======================================
# EDITAR ATLETA
# ======================================

@main_bp.route("/coach/editar/<int:atleta_id>", methods=["GET", "POST"])
@login_required
def editar_atleta(atleta_id):
    if current_user.email != "viru@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    atleta = User.query.get_or_404(atleta_id)

    if request.method == "POST":
        atleta.nombre = request.form["nombre"]
        atleta.email = request.form["email"]
        atleta.grupo = request.form.get("grupo")
        atleta.calendario_url = request.form.get("calendario_url")
        db.session.commit()
        flash("✅ Datos del atleta actualizados.", "success")
        return redirect(url_for("main.dashboard_entrenador"))

    return render_template("editar_atleta.html", atleta=atleta)

# ======================================
# ELIMINAR ATLETA
# ======================================

@main_bp.route("/coach/eliminar/<int:atleta_id>", methods=["POST"])
@login_required
def eliminar_atleta(atleta_id):
    if current_user.email != "viru@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    atleta = User.query.get_or_404(atleta_id)
    db.session.delete(atleta)
    db.session.commit()
    flash(f"❌ Atleta '{atleta.nombre}' eliminado.", "warning")
    return redirect(url_for("main.dashboard_entrenador"))
