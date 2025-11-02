from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, DiaPlan, Rutina, RutinaItem
from app.extensions import db

main_bp = Blueprint("main", __name__)


# ======================================
# HELPERS
# ======================================

def start_of_week(d: date) -> date:
    """Devuelve el lunes de la semana de la fecha dada."""
    return d - timedelta(days=d.weekday())


def week_dates(center: date | None = None):
    """Devuelve lista de fechas lunes-domingo."""
    base = center or date.today()
    start = start_of_week(base)
    return [start + timedelta(days=i) for i in range(7)]


# ======================================
# INDEX / LOGIN / LOGOUT
# ======================================

@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.email == "admin@vir.app":
            return redirect(url_for("main.dashboard_entrenador"))
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))
    return redirect(url_for("main.login"))


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Bienvenido {user.nombre} 👋", "success")
            if user.email == "admin@vir.app":
                return redirect(url_for("main.dashboard_entrenador"))
            return redirect(url_for("main.perfil_usuario", user_id=user.id))
        flash("❌ Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("main.login"))


# ======================================
# PERFIL DEL USUARIO (ATLETA)
# ======================================

@main_bp.route("/perfil")
@login_required
def perfil():
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))


@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id):
    # Entrenador puede ver cualquiera; atleta solo el suyo
    if current_user.email == "admin@vir.app":
        user = User.query.get_or_404(user_id)
    else:
        if current_user.id != user_id:
            flash("Acceso denegado.", "danger")
            return redirect(url_for("main.perfil"))
        user = current_user

    # Semana actual dinámica (lunes a domingo)
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    fechas = [lunes + timedelta(days=i) for i in range(7)]
    semana_str = f"Semana del {lunes.strftime('%d/%m')} al {(lunes + timedelta(days=6)).strftime('%d/%m')}"

    # Planes del atleta
    planes = {p.fecha: p for p in DiaPlan.query.filter(
        DiaPlan.user_id == user.id,
        DiaPlan.fecha.in_(fechas)
    ).all()}

    # Crear días faltantes
    for f in fechas:
        if f not in planes:
            nuevo = DiaPlan(user_id=user.id, fecha=f, plan_type="descanso")
            db.session.add(nuevo)
            planes[f] = nuevo
    db.session.commit()

    # Datos del gráfico (Propuesto vs Realizado)
    labels = [f.strftime("%d/%m") for f in fechas]
    propuesto = [planes[f].propuesto_score or 0 for f in fechas]
    realizado = [planes[f].realizado_score or 0 for f in fechas]

    # Rutinas más recientes
    rutinas = Rutina.query.order_by(Rutina.id.desc()).limit(6).all()

    return render_template(
        "perfil.html",
        user=user,
        fechas=fechas,
        planes=planes,
        labels=labels,
        propuesto=propuesto,
        realizado=realizado,
        rutinas=rutinas,
        semana_str=semana_str
    )


# ======================================
# GUARDAR PLAN DIARIO
# ======================================

@main_bp.route("/dia/save", methods=["POST"])
@login_required
def save_day():
    user_id = int(request.form["user_id"])
    if current_user.email != "admin@vir.app" and current_user.id != user_id:
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()
    plan_type = request.form.get("plan_type", "descanso")
    warmup = request.form.get("warmup", "")
    main = request.form.get("main", "")
    finisher = request.form.get("finisher", "")
    propuesto = int(request.form.get("propuesto_score", "0") or 0)
    realizado = int(request.form.get("realizado_score", "0") or 0)

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha)
        db.session.add(plan)

    plan.plan_type = plan_type
    plan.warmup = warmup
    plan.main = main
    plan.finisher = finisher
    plan.propuesto_score = propuesto
    plan.realizado_score = realizado
    db.session.commit()

    flash("✅ Día actualizado.", "success")
    return redirect(url_for("main.perfil_usuario", user_id=user_id))


# ======================================
# DASHBOARD ENTRENADOR
# ======================================

@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    atletas = User.query.filter(User.email != "admin@vir.app").all()
    return render_template("dashboard_entrenador.html", atletas=atletas)
