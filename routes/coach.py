# app/routes/coach.py
from __future__ import annotations

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, DiaPlan, Rutina, Ejercicio, AthleteLog, AthleteCheck

from . import main_bp, is_admin, week_dates, safe_parse_ymd, ensure_week_plans, list_repo_videos


@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if not is_admin():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutinas = Rutina.query.order_by(Rutina.id.desc()).all()
    ejercicios = Ejercicio.query.order_by(Ejercicio.id.desc()).all()
    atletas = User.query.filter(User.email != "admin@vir.app").order_by(User.id.desc()).all()

    available_videos = list_repo_videos()

    return render_template(
        "panel_entrenador.html",
        rutinas=rutinas,
        ejercicios=ejercicios,
        atletas=atletas,
        available_videos=available_videos,
    )


@main_bp.route("/admin/atletas/nuevo", methods=["POST"])
@login_required
def admin_nuevo_atleta():
    if not is_admin():
        flash("Solo admin", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    nombre = (request.form.get("nombre") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    grupo = (request.form.get("grupo") or "").strip()
    password = (request.form.get("password") or "").strip()

    if not nombre or not email or not password:
        flash("Faltan datos (nombre/email/password)", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    if User.query.filter_by(email=email).first():
        flash("Ese email ya existe", "warning")
        return redirect(url_for("main.dashboard_entrenador"))

    u = User(nombre=nombre, email=email, grupo=grupo, is_admin=False)
    u.set_password(password)

    db.session.add(u)
    db.session.commit()

    flash("✅ Atleta creado", "success")
    return redirect(url_for("main.dashboard_entrenador"))


@main_bp.route("/coach/planificador")
@login_required
def coach_planificador():
    if not is_admin():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    atletas = User.query.filter(User.email != "admin@vir.app").order_by(User.id.desc()).all()
    rutinas = Rutina.query.order_by(Rutina.id.desc()).all()

    user_id = request.args.get("user_id", type=int)
    if not user_id and atletas:
        user_id = atletas[0].id

    atleta = User.query.get(user_id) if user_id else None
    if not atleta:
        flash("No hay atletas", "warning")
        return render_template("dashboard_entrenador.html", atletas=atletas, rutinas=rutinas, atleta=None)

    center = safe_parse_ymd(request.args.get("center", ""), fallback=None)
    fechas = week_dates(center)

    planes = ensure_week_plans(atleta.id, fechas)
    semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"

    return render_template(
        "dashboard_entrenador.html",
        atletas=atletas,
        rutinas=rutinas,
        atleta=atleta,
        fechas=fechas,
        planes=planes,
        semana_str=semana_str,
        center=center,
    )


@main_bp.route("/dia/save", methods=["POST"])
@login_required
def save_day():
    if not is_admin():
        flash("Solo el admin puede editar entrenamientos", "danger")
        return redirect(url_for("main.perfil_redirect"))

    user_id = int(request.form["user_id"])
    fecha = safe_parse_ymd(request.form["fecha"])

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha)
        db.session.add(plan)

    # si el atleta bloqueó el día
    if hasattr(plan, "puede_entrenar") and (getattr(plan, "puede_entrenar", "si") == "no"):
        flash("🚫 El atleta marcó este día como 'No puedo entrenar'.", "warning")
        return redirect(url_for("main.coach_planificador", user_id=user_id, center=fecha.isoformat()))

    plan_type = (request.form.get("plan_type") or "Descanso").strip()
    plan.plan_type = plan_type

    if plan_type.lower() == "fuerza":
        rutina_select = (request.form.get("rutina_select") or "").strip()
        plan.main = rutina_select
        plan.warmup = (request.form.get("warmup") or "").strip()
        plan.finisher = (request.form.get("finisher") or "").strip()
    else:
        plan.warmup = (request.form.get("warmup") or "").strip()
        plan.main = (request.form.get("main") or "").strip()
        plan.finisher = (request.form.get("finisher") or "").strip()

    try:
        plan.propuesto_score = int(request.form.get("propuesto_score", 0))
    except Exception:
        plan.propuesto_score = 0

    db.session.commit()
    flash("✅ Día guardado", "success")
    return redirect(url_for("main.coach_planificador", user_id=user_id, center=fecha.isoformat()))


@main_bp.route("/crear_rutina", methods=["POST"])
@login_required
def crear_rutina():
    if not is_admin():
        flash("Solo el admin puede crear rutinas", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    nombre = (request.form.get("nombre") or "").strip()
    tipo = (request.form.get("tipo") or "").strip()
    descripcion = (request.form.get("descripcion") or "").strip()

    if not nombre:
        flash("El nombre es obligatorio", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    nueva = Rutina(nombre=nombre, tipo=tipo, descripcion=descripcion, created_by=current_user.id)
    db.session.add(nueva)
    db.session.commit()

    flash("✅ Rutina creada", "success")
    return redirect(url_for("main.dashboard_entrenador"))


@main_bp.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
def admin_delete_user(user_id: int):
    if not is_admin():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    user = User.query.get_or_404(user_id)
    if user.email == "admin@vir.app":
        flash("No se puede eliminar admin", "warning")
        return redirect(url_for("main.dashboard_entrenador"))

    DiaPlan.query.filter_by(user_id=user.id).delete()
    AthleteLog.query.filter_by(user_id=user.id).delete()
    AthleteCheck.query.filter_by(user_id=user.id).delete()

    db.session.delete(user)
    db.session.commit()

    flash("✅ Atleta eliminado", "success")
    return redirect(url_for("main.dashboard_entrenador"))
