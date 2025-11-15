from __future__ import annotations

from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import Any, Dict, List

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import InternalError
from sqlalchemy import text

from app.models import User, DiaPlan, Rutina
from app.extensions import db

# =============================================================================
# Blueprint
# =============================================================================
main_bp = Blueprint("main", __name__)

# =============================================================================
# Utilidades de fechas
# =============================================================================
def start_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())

def week_dates(center: date | None = None) -> List[date]:
    base = center or date.today()
    start = start_of_week(base)
    return [start + timedelta(days=i) for i in range(7)]

def month_dates(year: int, month: int) -> List[date]:
    _, last = monthrange(year, month)
    return [date(year, month, d) for d in range(1, last + 1)]

def safe_parse_ymd(s: str, fallback: date | None = None) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            return fallback or date.today()

# =============================================================================
# Serializadores
# =============================================================================
def serialize_user(u: User) -> Dict[str, Any]:
    return {
        "id": u.id,
        "nombre": u.nombre,
        "email": u.email,
        "grupo": u.grupo or "",
    }

def serialize_rutina(r: Rutina) -> Dict[str, Any]:
    return {
        "id": r.id,
        "nombre": r.nombre,
        "tipo": (r.tipo or "").lower(),
        "descripcion": r.descripcion or "",
        "created_by": r.created_by,
    }

def serialize_plan(p: DiaPlan) -> Dict[str, Any]:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "fecha": p.fecha.strftime("%Y-%m-%d"),
        "plan_type": (p.plan_type or "descanso").lower(),
        "warmup": p.warmup or "",
        "main": p.main or "",
        "finisher": p.finisher or "",
        "propuesto_score": p.propuesto_score or 0,
        "realizado_score": p.realizado_score or 0,
        "puede_entrenar": p.puede_entrenar or "",
        "dificultad": p.dificultad or "",
        "comentario_atleta": p.comentario_atleta or "",
    }

# =============================================================================
# Home / Auth
# =============================================================================
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
            if user.email == "admin@vir.app":
                return redirect(url_for("main.dashboard_entrenador"))
            return redirect(url_for("main.perfil_usuario", user_id=user.id))
        flash("Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")

@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("main.login"))

# =============================================================================
# Perfil redirección
# =============================================================================
@main_bp.route("/perfil", endpoint="perfil")
@login_required
def perfil_redirect():
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

# =============================================================================
# Perfil usuario
# =============================================================================
@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id: int):
    try:
        user = User.query.get_or_404(user_id)

        if current_user.email != "admin@vir.app" and current_user.id != user.id:
            flash("Acceso denegado.", "danger")
            return redirect(url_for("main.perfil", user_id=current_user.id))

        fechas = week_dates()
        planes_db = DiaPlan.query.filter(
            DiaPlan.user_id == user.id,
            DiaPlan.fecha.in_(fechas)
        ).all()

        planes = {p.fecha: p for p in planes_db}

        # Crear días que faltan
        for f in fechas:
            if f not in planes:
                nuevo = DiaPlan(user_id=user.id, fecha=f, plan_type="descanso")
                db.session.add(nuevo)
                planes[f] = nuevo
        db.session.commit()

        # Mes para calendario mensual
        hoy = date.today()
        dias_mes = month_dates(hoy.year, hoy.month)
        planes_mes_db = DiaPlan.query.filter(
            DiaPlan.user_id == user.id,
            DiaPlan.fecha.in_(dias_mes)
        ).all()
        planes_mes = {p.fecha: p for p in planes_mes_db}

        semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"

        rutinas = Rutina.query.order_by(Rutina.id.desc()).all()

        # Gráficos
        labels = [f.strftime("%d/%m") for f in fechas]
        propuesto = [planes[f].propuesto_score or 0 for f in fechas]
        realizado = [planes[f].realizado_score or 0 for f in fechas]

        return render_template(
            "perfil.html",
            user=user,
            fechas=fechas,
            planes=planes,
            labels=labels,
            propuesto=propuesto,
            realizado=realizado,
            semana_str=semana_str,
            hoy=hoy,
            dias_mes=dias_mes,
            planes_mes=planes_mes,
            rutinas=rutinas,
        )

    except Exception as e:
        print("ERROR PERFIL:", e)
        flash("Error cargando perfil.", "danger")
        return redirect(url_for("main.index"))

# =============================================================================
# Guardar día (ADMIN)
# =============================================================================
@main_bp.route("/dia/save", methods=["POST"])
@login_required
def save_day():
    if current_user.email != "admin@vir.app":
        flash("Solo el admin puede editar el entrenamiento.", "danger")
        return redirect(url_for("main.perfil"))

    user_id = int(request.form["user_id"])
    fecha = safe_parse_ymd(request.form["fecha"])

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha)
        db.session.add(plan)

    plan.plan_type = request.form.get("plan_type", "descanso")
    plan.warmup = request.form.get("warmup", "")
    plan.main = request.form.get("main", "")
    plan.finisher = request.form.get("finisher", "")
    plan.propuesto_score = int(request.form.get("propuesto_score", 0))

    db.session.commit()
    flash("Día actualizado.", "success")
    return redirect(url_for("main.perfil_usuario", user_id=user_id))

# =============================================================================
# Guardar feedback atleta
# =============================================================================
@main_bp.route("/dia/feedback", methods=["POST"])
@login_required
def save_feedback():
    user_id = int(request.form["user_id"])
    fecha = safe_parse_ymd(request.form["fecha"])

    if current_user.id != user_id:
        flash("No puedes editar otro perfil.", "danger")
        return redirect(url_for("main.perfil"))

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha)
        db.session.add(plan)

    plan.puede_entrenar = request.form.get("puede_entrenar", "")
    plan.dificultad = request.form.get("dificultad", "")
    plan.comentario_atleta = request.form.get("comentario_atleta", "")

    db.session.commit()
    flash("Feedback guardado.", "success")
    return redirect(url_for("main.perfil_usuario", user_id=user_id))

# =============================================================================
# Crear rutina
# =============================================================================
@main_bp.route("/crear_rutina", methods=["POST"])
@login_required
def crear_rutina():
    if current_user.email != "admin@vir.app":
        flash("Solo el admin puede crear rutinas.", "danger")
        return redirect(url_for("main.perfil"))

    nombre = request.form.get("nombre")
    tipo = request.form.get("tipo")
    descripcion = request.form.get("descripcion")

    nueva = Rutina(nombre=nombre, tipo=tipo, descripcion=descripcion, created_by=current_user.id)
    db.session.add(nueva)
    db.session.commit()

    flash("Rutina creada.", "success")
    return redirect(request.referrer or url_for("main.dashboard_entrenador"))

# =============================================================================
# Dashboard entrenador
# =============================================================================
@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    atletas_db = User.query.filter(User.email != "admin@vir.app").all()
    rutinas_db = Rutina.query.order_by(Rutina.id.desc()).all()
    hoy = date.today()

    return render_template(
        "dashboard_entrenador.html",
        atletas=atletas_db,
        rutinas=rutinas_db,
        hoy=hoy
    )

# =============================================================================
# Asignar bloque (Drag & Drop)
# =============================================================================
@main_bp.route("/asignar_bloque", methods=["POST"])
@login_required
def asignar_bloque():
    if current_user.email != "admin@vir.app":
        return jsonify({"status": "error", "msg": "No autorizado"}), 403

    data = request.get_json()
    atleta_id = data.get("user_id")
    rutina_id = data.get("rutina_id")
    fecha = safe_parse_ymd(data.get("fecha"))

    rutina = Rutina.query.get(rutina_id)
    if not rutina:
        return jsonify({"status": "error", "msg": "Rutina no encontrada"}), 404

    plan = DiaPlan.query.filter_by(user_id=atleta_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=atleta_id, fecha=fecha)
        db.session.add(plan)

    plan.plan_type = rutina.tipo
    plan.main = rutina.descripcion

    db.session.commit()
    return jsonify({"status": "ok", "plan": serialize_plan(plan)})

# =============================================================================
# Setup rápido
# =============================================================================
@main_bp.route("/setup-admin")
def setup_admin():
    email = "admin@vir.app"
    if User.query.filter_by(email=email).first():
        return "Admin ya existe."
    admin = User(nombre="Admin", email=email, grupo="Entrenador")
    admin.set_password("Admin123")
    db.session.add(admin)
    db.session.commit()
    return "Admin creado."

