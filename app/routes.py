from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, render_template_string
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, DiaPlan, Rutina
from app.extensions import db

main_bp = Blueprint("main", __name__)


def start_of_week(d: date) -> date:
    return d - timedelta(days=(d.weekday() % 7))


def week_dates(center: date | None = None):
    base = center or date.today()
    start = start_of_week(base)
    return [start + timedelta(days=i) for i in range(7)]


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


@main_bp.route("/perfil")
@login_required
def perfil():
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))


@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id):
    if current_user.email == "admin@vir.app":
        user = User.query.get_or_404(user_id)
    else:
        if current_user.id != user_id:
            flash("Acceso denegado.", "danger")
            return redirect(url_for("main.perfil"))
        user = current_user

    fechas = week_dates()
    planes = {p.fecha: p for p in DiaPlan.query.filter(
        DiaPlan.user_id == user.id,
        DiaPlan.fecha.in_(fechas)
    ).all()}

    # Crear placeholders si faltan días
    for f in fechas:
        if f not in planes:
            nuevo = DiaPlan(user_id=user.id, fecha=f, plan_type="descanso")
            db.session.add(nuevo)
            planes[f] = nuevo
    db.session.commit()

    labels = [f.strftime("%d/%m") for f in fechas]
    propuesto = [planes[f].propuesto_score or 0 for f in fechas]
    realizado = [planes[f].realizado_score or 0 for f in fechas]

    try:
        rutinas = Rutina.query.order_by(Rutina.id.desc()).limit(6).all()
    except Exception:
        rutinas = []

    # (opcional) semana_str para el título
    semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"

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


@main_bp.route("/dia/save", methods=["POST"])
@login_required
def save_day():
    user_id = int(request.form["user_id"])
    if current_user.email != "admin@vir.app" and current_user.id != user_id:
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    fecha_str = request.form["fecha"].strip()
    # Parseo robusto (YYYY-MM-DD o con hora)
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        try:
            fecha = datetime.fromisoformat(fecha_str).date()
        except ValueError:
            flash("Fecha inválida.", "danger")
            return redirect(url_for("main.perfil_usuario", user_id=user_id))

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


@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))
    atletas = User.query.filter(User.email != "admin@vir.app").all()
    return render_template("dashboard_entrenador.html", atletas=atletas)


# ================================
# ✅ RUTA FALTANTE: listar_rutinas
# ================================
@main_bp.route("/rutinas")
@login_required
def listar_rutinas():
    # No dependemos de un template extra para evitar errores de fichero
    try:
        rutinas = Rutina.query.order_by(Rutina.id.desc()).all()
    except Exception:
        rutinas = []

    html = """
    <!doctype html>
    <html lang="es">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Rutinas</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-dark text-light">
      <div class="container py-4">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h3 class="mb-0">📚 Biblioteca de Rutinas</h3>
          <a href="{{ url_for('main.perfil') }}" class="btn btn-outline-light btn-sm">Volver al perfil</a>
        </div>

        {% if rutinas %}
          <div class="row">
            {% for r in rutinas %}
            <div class="col-md-4 mb-3">
              <div class="card bg-secondary text-light h-100">
                <div class="card-body">
                  <h5 class="card-title">{{ r.nombre }}</h5>
                  <p class="card-text">{{ r.descripcion or '' }}</p>
                  {% if r.items %}
                    <ul class="small">
                      {% for it in r.items %}
                        <li><strong>{{ it.nombre }}</strong>{% if it.reps %} — {{ it.reps }}{% endif %}</li>
                      {% endfor %}
                    </ul>
                  {% else %}
                    <p class="small text-dark-emphasis">Sin items todavía.</p>
                  {% endif %}
                </div>
              </div>
            </div>
            {% endfor %}
          </div>
        {% else %}
          <div class="alert alert-secondary">No hay rutinas cargadas.</div>
        {% endif %}
      </div>
    </body>
    </html>
    """
    return render_template_string(html, rutinas=rutinas)
