from __future__ import annotations

from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import Dict, Any, List

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import text
from sqlalchemy.exc import InternalError

from app.extensions import db
from app.models import User, DiaPlan, Rutina

main_bp = Blueprint("main", __name__)


# ========== UTILIDADES FECHAS ==========
def start_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())

def week_dates(center=None):
    center = center or date.today()
    start = start_of_week(center)
    return [start + timedelta(days=i) for i in range(7)]

def month_dates(year, month):
    _, last = monthrange(year, month)
    return [date(year, month, d) for d in range(1, last + 1)]

def safe_parse_ymd(s, fallback=None):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except:
        return fallback or date.today()


# ========== SERIALIZADORES ==========
def serialize_user(u):
    return {
        "id": u.id,
        "nombre": u.nombre,
        "email": u.email,
        "grupo": u.grupo
    }

def serialize_plan(p):
    return {
        "id": p.id,
        "user_id": p.user_id,
        "fecha": p.fecha.isoformat(),
        "plan_type": p.plan_type,
        "warmup": p.warmup,
        "main": p.main,
        "finisher": p.finisher,
        "puede_entrenar": p.puede_entrenar,
        "dificultad": p.dificultad,
        "comentario_atleta": p.comentario_atleta,
        "propuesto_score": p.propuesto_score,
        "realizado_score": p.realizado_score
    }


# ========== HOME, LOGIN, LOGOUT ==========
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
        email = request.form["email"].lower().strip()
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Bienvenido {user.nombre}", "success")
            return redirect(url_for("main.index"))

        flash("Usuario o contraseña incorrectos", "danger")

    return render_template("login.html")


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("main.login"))


# ========== PERFIL USUARIO ==========
@main_bp.route("/perfil")
@login_required
def perfil_redirect():
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))


@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id):
    user = User.query.get_or_404(user_id)

    # Seguridad
    if current_user.email != "admin@vir.app" and current_user.id != user.id:
        flash("No podes ver el perfil de otro atleta", "danger")
        return redirect(url_for("main.perfil_redirect"))

    fechas = week_dates()
    dias_mes = month_dates(date.today().year, date.today().month)
    hoy = date.today()

    # Cargar planes
    planes_db = DiaPlan.query.filter(
        DiaPlan.user_id == user.id,
        DiaPlan.fecha.in_(fechas + dias_mes)
    ).all()

    planes = {p.fecha: p for p in planes_db}
    planes_mes = {p.fecha: p for p in planes_db}

    # Crear días vacíos
    for f in fechas + dias_mes:
        if f not in planes:
            nuevo = DiaPlan(user_id=user.id, fecha=f, plan_type="descanso")
            db.session.add(nuevo)
            planes[f] = nuevo
            planes_mes[f] = nuevo
    db.session.commit()

    # Scores
    labels = [f.strftime("%d/%m") for f in fechas]
    propuesto = [planes[f].propuesto_score or 0 for f in fechas]
    realizado = [planes[f].realizado_score or 0 for f in fechas]

    rutinas = Rutina.query.order_by(Rutina.id.desc()).all()

    semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"

    return render_template(
        "perfil.html",
        user=user,
        fechas=fechas,
        planes=planes,
        planes_mes=planes_mes,
        dias_mes=dias_mes,
        labels=labels,
        propuesto=propuesto,
        realizado=realizado,
        rutinas=rutinas,
        hoy=hoy,
        semana_str=semana_str
    )


# ========== ADMIN EDITA DÍA ==========
@main_bp.route("/dia/save", methods=["POST"])
@login_required
def save_day():
    if current_user.email != "admin@vir.app":
        flash("Solo el admin puede editar entrenamientos", "danger")
        return redirect(url_for("main.index"))

    user_id = int(request.form["user_id"])
    fecha = safe_parse_ymd(request.form["fecha"])

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha)
        db.session.add(plan)

    plan.plan_type = request.form.get("plan_type")
    plan.warmup = request.form.get("warmup", "")
    plan.main = request.form.get("main", "")
    plan.finisher = request.form.get("finisher", "")

    plan.propuesto_score = int(request.form.get("propuesto_score", 0))
    plan.realizado_score = int(request.form.get("realizado_score", 0))

    db.session.commit()
    flash("Día actualizado correctamente", "success")
    return redirect(url_for("main.perfil_usuario", user_id=user_id))


# ========== ATLETA GUARDA FEEDBACK ==========
@main_bp.route("/dia/feedback", methods=["POST"])
@login_required
def save_feedback():
    user_id = int(request.form["user_id"])
    fecha = safe_parse_ymd(request.form["fecha"])

    if current_user.id != user_id:
        flash("No podés modificar otro atleta", "danger")
        return redirect(url_for("main.perfil_redirect"))

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        flash("El día aún no está creado", "danger")
        return redirect(url_for("main.perfil_usuario", user_id=user_id))

    plan.puede_entrenar = request.form.get("puede_entrenar")
    plan.dificultad = request.form.get("dificultad")
    plan.comentario_atleta = request.form.get("comentario_atleta", "")

    db.session.commit()
    flash("Feedback guardado correctamente", "success")
    return redirect(url_for("main.perfil_usuario", user_id=user_id))


# ========== ASIGNAR BLOQUE (DRAG & DROP) ==========
@main_bp.route("/asignar_bloque", methods=["POST"])
@login_required
def asignar_bloque():
    if current_user.email != "admin@vir.app":
        return jsonify({"status": "error", "msg": "Sin permisos"}), 403

    data = request.get_json()
    atleta_id = data["user_id"]
    rutina_id = data["rutina_id"]
    fecha = safe_parse_ymd(data["fecha"])

    rutina = Rutina.query.get(rutina_id)
    plan = DiaPlan.query.filter_by(user_id=atleta_id, fecha=fecha).first()

    if not plan:
        plan = DiaPlan(user_id=atleta_id, fecha=fecha)

    plan.plan_type = rutina.tipo
    plan.main = rutina.descripcion
    db.session.add(plan)
    db.session.commit()

    return jsonify({"status": "ok", "plan": serialize_plan(plan)})


# ========== DASHBOARD ADMIN ==========
@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if current_user.email != "admin@vir.app":
        flash("Solo admin", "danger")
        return redirect(url_for("main.index"))

    atletas = User.query.filter(User.email != "admin@vir.app").all()
    rutinas = Rutina.query.order_by(Rutina.id.desc()).all()

    return render_template(
        "dashboard_entrenador.html",
        atletas=[serialize_user(a) for a in atletas],
        rutinas=[{
            "id": r.id,
            "nombre": r.nombre,
            "tipo": r.tipo,
            "descripcion": r.descripcion
        } for r in rutinas]
    )


# ========== CREAR RUTINA ==========
@main_bp.route("/crear_rutina", methods=["POST"])
@login_required
def crear_rutina():
    if current_user.email != "admin@vir.app":
        flash("Solo admin puede crear rutinas", "danger")
        return redirect(url_for("main.index"))

    nombre = request.form.get("nombre")
    tipo = request.form.get("tipo")
    descripcion = request.form.get("descripcion")

    nueva = Rutina(nombre=nombre, tipo=tipo, descripcion=descripcion, created_by=current_user.id)
    db.session.add(nueva)
    db.session.commit()

    flash("Rutina creada correctamente", "success")
    return redirect(request.referrer or url_for("main.dashboard_entrenador"))


# ========== FIX DB Y UTILS ==========
@main_bp.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})
