# app/routes.py
from __future__ import annotations

from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import Any, Dict, List

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import InternalError
from sqlalchemy import text

from werkzeug.utils import secure_filename
import os

from app.models import User, DiaPlan, Rutina, Ejercicio
from app.extensions import db


# =============================================================
# BLUEPRINT
# =============================================================
main_bp = Blueprint("main", __name__)


# =============================================================
# FECHAS / UTILIDADES
# =============================================================
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
    """Parse seguro YYYY-MM-DD"""
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            return fallback or date.today()


# =============================================================
# SERIALIZADORES SEGUROS
# =============================================================
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
        "tipo": r.tipo,
        "descripcion": r.descripcion,
        "created_by": r.created_by,
    }


def serialize_plan(p: DiaPlan) -> Dict[str, Any]:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "fecha": p.fecha.strftime("%Y-%m-%d"),
        "plan_type": p.plan_type or "descanso",
        "warmup": p.warmup or "",
        "main": p.main or "",
        "finisher": p.finisher or "",
        "propuesto_score": p.propuesto_score or 0,
        "realizado_score": p.realizado_score or 0,
        "puede_entrenar": p.puede_entrenar or "",
        "dificultad": p.dificultad or "",
        "comentario_atleta": p.comentario_atleta or "",
    }


# =============================================================
# HOME / LOGIN
# =============================================================
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
            flash(f"Bienvenido {user.nombre}", "success")
            if user.email == "admin@vir.app":
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


# =============================================================
# PERFIL → REDIRECT
# =============================================================
@main_bp.route("/perfil")
@login_required
def perfil_redirect():
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))


# =============================================================
# PERFIL DE USUARIO (ATLETA)
# =============================================================
@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id: int):

    try:
        user = User.query.get_or_404(user_id)

        # Seguridad: atleta no puede ver otro perfil
        if current_user.email != "admin@vir.app" and current_user.id != user.id:
            flash("Acceso denegado", "danger")
            return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

        # Semana + planes
        fechas = week_dates()
        planes_db = DiaPlan.query.filter(
            DiaPlan.user_id == user.id,
            DiaPlan.fecha.in_(fechas)
        ).all()

        planes = {p.fecha: p for p in planes_db}

        # Crear entries vacías que falten
        for f in fechas:
            if f not in planes:
                nuevo = DiaPlan(user_id=user.id, fecha=f, plan_type="descanso")
                planes[f] = nuevo
                db.session.add(nuevo)
        db.session.commit()

        labels = [f.strftime("%d/%m") for f in fechas]
        propuesto = [planes[f].propuesto_score or 0 for f in fechas]
        realizado = [planes[f].realizado_score or 0 for f in fechas]

        # MES COMPLETO
        hoy = date.today()
        dias_mes = month_dates(hoy.year, hoy.month)
        planes_mes = {
            p.fecha: p
            for p in DiaPlan.query.filter(
                DiaPlan.user_id == user.id,
                DiaPlan.fecha.in_(dias_mes)
            ).all()
        }

        semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"

        rutinas = Rutina.query.order_by(Rutina.id.desc()).all()

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
        db.session.rollback()
        flash(f"Error cargando perfil: {e}", "danger")
        return redirect(url_for("main.index"))


# =============================================================
# ADMIN GUARDA ENTRENAMIENTO DEL DÍA
# =============================================================
@main_bp.route("/dia/save", methods=["POST"])
@login_required
def save_day():

    if current_user.email != "admin@vir.app":
        flash("Solo el admin puede editar entrenamientos", "danger")
        return redirect(url_for("main.perfil_redirect"))

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
    flash("Entrenamiento actualizado", "success")

    return redirect(url_for("main.perfil_usuario", user_id=user_id))


# =============================================================
# ATLETA GUARDA FEEDBACK
# =============================================================
@main_bp.route("/dia/feedback", methods=["POST"])
@login_required
def save_feedback():

    user_id = int(request.form["user_id"])

    if current_user.id != user_id and current_user.email != "admin@vir.app":
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    fecha = safe_parse_ymd(request.form["fecha"])
    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()

    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha)
        db.session.add(plan)

    plan.puede_entrenar = request.form.get("puede_entrenar", "")
    plan.dificultad = request.form.get("dificultad", "")
    plan.comentario_atleta = request.form.get("comentario_atleta", "")
    plan.realizado_score = int(request.form.get("realizado_score", 0))

    db.session.commit()

    flash("Feedback guardado correctamente", "success")
    return redirect(url_for("main.perfil_usuario", user_id=user_id))


# =============================================================
# DASHBOARD ENTRENADOR
# =============================================================
@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    atletas_db = User.query.filter(User.email != "admin@vir.app").all()
    rutinas_db = Rutina.query.order_by(Rutina.id.desc()).all()
    ejercicios_db = Ejercicio.query.order_by(Ejercicio.nombre).all()

    atletas = [serialize_user(a) for a in atletas_db]
    rutinas = [serialize_rutina(r) for r in rutinas_db]
    hoy = date.today()

    return render_template(
        "dashboard_entrenador.html",
        atletas=atletas,
        rutinas=rutinas,
        ejercicios=ejercicios_db,
        hoy=hoy
    )


# =============================================================
# CRUD USUARIOS
# =============================================================
@main_bp.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
def admin_delete_user(user_id: int):

    if current_user.email != "admin@vir.app":
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    user = User.query.get_or_404(user_id)

    if user.email == "admin@vir.app":
        flash("No se puede eliminar admin", "warning")
        return redirect(url_for("main.dashboard_entrenador"))

    DiaPlan.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()

    flash("Atleta eliminado", "success")
    return redirect(url_for("main.dashboard_entrenador"))


# =============================================================
# CREAR RUTINA
# =============================================================
@main_bp.route("/crear_rutina", methods=["POST"])
@login_required
def crear_rutina():

    if current_user.email != "admin@vir.app":
        flash("Solo el admin puede crear rutinas", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    nombre = request.form.get("nombre", "").strip()
    tipo = request.form.get("tipo", "").strip()
    descripcion = request.form.get("descripcion", "").strip()

    if not nombre:
        flash("El nombre es obligatorio", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    nueva = Rutina(
        nombre=nombre,
        tipo=tipo,
        descripcion=descripcion,
        created_by=current_user.id
    )
    db.session.add(nueva)
    db.session.commit()

    flash("Rutina creada correctamente", "success")
    return redirect(url_for("main.dashboard_entrenador"))


# =============================================================
# CREAR EJERCICIO DEL BANCO (CON VIDEO)
# =============================================================
@main_bp.route("/admin/ejercicios/nuevo", methods=["POST"])
@login_required
def admin_nuevo_ejercicio():

    if current_user.email != "admin@vir.app":
        flash("Solo el admin puede crear ejercicios", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    nombre = request.form.get("nombre", "").strip()
    categoria = request.form.get("categoria", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    file = request.files.get("video")

    if not nombre or not file:
        flash("Falta el nombre o el vídeo del ejercicio", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    filename = secure_filename(file.filename)
    if not filename:
        flash("Nombre de archivo no válido", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    upload_folder = os.path.join(current_app.static_folder, "videos_ejercicios")
    os.makedirs(upload_folder, exist_ok=True)

    save_path = os.path.join(upload_folder, filename)
    file.save(save_path)

    ejercicio = Ejercicio(
        nombre=nombre,
        categoria=categoria,
        descripcion=descripcion,
        video_filename=filename
    )

    db.session.add(ejercicio)
    db.session.commit()

    flash("Ejercicio subido al banco correctamente", "success")
    return redirect(url_for("main.dashboard_entrenador"))


# =============================================================
# HEALTHCHECK
# =============================================================
@main_bp.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})
