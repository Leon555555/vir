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
from sqlalchemy import text

from werkzeug.utils import secure_filename
import os

from app.models import User, DiaPlan, Rutina, Ejercicio, RutinaItem
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
        "puede_entrenar": getattr(p, "puede_entrenar", "") or "",
        "dificultad": getattr(p, "dificultad", "") or "",
        "comentario_atleta": getattr(p, "comentario_atleta", "") or "",
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

        # Rutinas (para tab rutinas en el perfil)
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
#   - Guarda videos en: static/videos/
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

    upload_folder = os.path.join(current_app.static_folder, "videos")
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
# CONSTRUCTOR DE RUTINA (VER / EDITAR EJERCICIOS)
# =============================================================
@main_bp.route("/rutinas/<int:rutina_id>/builder")
@login_required
def rutina_builder(rutina_id: int):
    if current_user.email != "admin@vir.app":
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    items = RutinaItem.query.filter_by(rutina_id=rutina.id).order_by(RutinaItem.id).all()
    ejercicios = Ejercicio.query.order_by(Ejercicio.nombre).all()

    return render_template(
        "rutina_builder.html",
        rutina=rutina,
        items=items,
        ejercicios=ejercicios
    )

# =============================================================
# AÑADIR EJERCICIO DEL BANCO A UNA RUTINA
# =============================================================
@main_bp.route("/rutinas/<int:rutina_id>/add_item", methods=["POST"])
@login_required
def rutina_add_item(rutina_id: int):
    if current_user.email != "admin@vir.app":
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    ejercicio_id = request.form.get("ejercicio_id", type=int)

    if not ejercicio_id:
        flash("Falta el ejercicio a añadir", "danger")
        return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))

    ejercicio = Ejercicio.query.get_or_404(ejercicio_id)

    series = request.form.get("series", "").strip()
    reps = request.form.get("reps", "").strip()
    descanso = request.form.get("descanso", "").strip()
    notas = request.form.get("notas", "").strip()

    item = RutinaItem(
        rutina_id=rutina.id,
        ejercicio_id=ejercicio.id,
        nombre=ejercicio.nombre,
        series=series,
        reps=reps,
        descanso=descanso,
        notas=notas,
        # OJO: ruta relativa para el <video> en templates
        video_url=f"videos/{ejercicio.video_filename}",
    )

    db.session.add(item)
    db.session.commit()

    flash("Ejercicio añadido a la rutina", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))

# =============================================================
# ACTUALIZAR ITEM DE RUTINA (lo necesitabas por el error)
# =============================================================
@main_bp.route("/rutinas/<int:rutina_id>/items/<int:item_id>/update", methods=["POST"])
@login_required
def rutina_update_item(rutina_id: int, item_id: int):
    if current_user.email != "admin@vir.app":
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    item = RutinaItem.query.get_or_404(item_id)
    if item.rutina_id != rutina_id:
        flash("Item inválido", "danger")
        return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))

    item.series = request.form.get("series", "").strip()
    item.reps = request.form.get("reps", "").strip()
    item.descanso = request.form.get("descanso", "").strip()
    item.notas = request.form.get("notas", "").strip()

    db.session.commit()
    flash("Cambios guardados", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))

# =============================================================
# ELIMINAR EJERCICIO DE UNA RUTINA
# =============================================================
@main_bp.route("/rutinas/<int:rutina_id>/items/<int:item_id>/delete", methods=["POST"])
@login_required
def rutina_delete_item(rutina_id: int, item_id: int):
    if current_user.email != "admin@vir.app":
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    item = RutinaItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()

    flash("Ejercicio eliminado de la rutina", "info")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))

# =============================================================
# PLANIFICADOR (COACH) - PASO 1
# =============================================================
@main_bp.route("/coach/planificador/<int:user_id>")
@login_required
def coach_planificador(user_id: int):
    if current_user.email != "admin@vir.app":
        return "Acceso denegado", 403

    atleta = User.query.get_or_404(user_id)
    center_date = safe_parse_ymd(request.args.get("center", ""), fallback=date.today())

    fechas = week_dates(center_date)

    planes_db = DiaPlan.query.filter(
        DiaPlan.user_id == atleta.id,
        DiaPlan.fecha.in_(fechas)
    ).all()

    planes = {p.fecha: p for p in planes_db}

    # crea días faltantes
    for f in fechas:
        if f not in planes:
            nuevo = DiaPlan(user_id=atleta.id, fecha=f, plan_type="descanso")
            planes[f] = nuevo
            db.session.add(nuevo)
    db.session.commit()

    semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"

    # rutinas disponibles para asignar
    rutinas = Rutina.query.order_by(Rutina.id.desc()).all()

    return render_template(
        "coach/planificador.html",
        atleta=atleta,
        fechas=fechas,
        planes=planes,
        rutinas=rutinas,
        semana_str=semana_str,
        center=center_date
    )

# =============================================================
# GUARDAR DÍA DESDE PLANIFICADOR (COACH)
# =============================================================
@main_bp.route("/coach/planificador/<int:user_id>/guardar_dia", methods=["POST"])
@login_required
def coach_guardar_dia(user_id: int):
    if current_user.email != "admin@vir.app":
        return "Acceso denegado", 403

    atleta = User.query.get_or_404(user_id)
    fecha = safe_parse_ymd(request.form.get("fecha", ""), fallback=date.today())
    center = safe_parse_ymd(request.form.get("center", ""), fallback=fecha)

    plan = DiaPlan.query.filter_by(user_id=atleta.id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=atleta.id, fecha=fecha)
        db.session.add(plan)

    plan.plan_type = request.form.get("plan_type", "descanso")
    plan.warmup = request.form.get("warmup", "")
    plan.finisher = request.form.get("finisher", "")
    plan.propuesto_score = int(request.form.get("propuesto_score", 0))

    # asignar rutina (guarda referencia en main como: RUTINA:ID)
    rutina_id = request.form.get("rutina_id", type=int)
    if rutina_id:
        plan.main = f"RUTINA:{rutina_id}"
    else:
        plan.main = request.form.get("main", "")

    db.session.commit()
    flash("Día guardado ✔", "success")

    return redirect(url_for("main.coach_planificador", user_id=atleta.id, center=center.isoformat()))

# =============================================================
# COPIAR SEMANA COMPLETA (COACH) - PASO 2
# =============================================================
@main_bp.route("/coach/planificador/<int:user_id>/copiar_semana", methods=["POST"])
@login_required
def coach_copiar_semana(user_id: int):
    if current_user.email != "admin@vir.app":
        return "Acceso denegado", 403

    atleta = User.query.get_or_404(user_id)
    center = safe_parse_ymd(request.form.get("center", ""), fallback=date.today())

    semana_origen = week_dates(center)
    semana_destino = [d + timedelta(days=7) for d in semana_origen]

    planes_origen = {
        p.fecha: p
        for p in DiaPlan.query.filter(
            DiaPlan.user_id == atleta.id,
            DiaPlan.fecha.in_(semana_origen)
        ).all()
    }

    for f_o, f_d in zip(semana_origen, semana_destino):
        plan_o = planes_origen.get(f_o)
        if not plan_o:
            continue

        plan_d = DiaPlan.query.filter_by(user_id=atleta.id, fecha=f_d).first()
        if not plan_d:
            plan_d = DiaPlan(user_id=atleta.id, fecha=f_d)
            db.session.add(plan_d)

        # copia lo planificado
        plan_d.plan_type = plan_o.plan_type
        plan_d.warmup = plan_o.warmup
        plan_d.main = plan_o.main
        plan_d.finisher = plan_o.finisher
        plan_d.propuesto_score = plan_o.propuesto_score

        # limpia feedback
        plan_d.realizado_score = 0
        plan_d.puede_entrenar = None
        plan_d.dificultad = None
        plan_d.comentario_atleta = None

    db.session.commit()
    flash("Semana copiada correctamente ✔", "success")

    return redirect(url_for("main.coach_planificador", user_id=atleta.id, center=(center + timedelta(days=7)).isoformat()))

# =============================================================
# PARCHE: CREAR COLUMNA ejercicio_id EN rutina_item (si hace falta)
# =============================================================
@main_bp.route("/fix-ejercicio-columna")
@login_required
def fix_ejercicio_columna():
    if current_user.email != "admin@vir.app":
        return "Acceso denegado", 403

    try:
        db.session.execute(text("""
            ALTER TABLE rutina_item
            ADD COLUMN IF NOT EXISTS ejercicio_id INTEGER;
        """))

        db.session.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.constraint_column_usage
                WHERE table_name = 'rutina_item'
                  AND constraint_name = 'rutina_item_ejercicio_id_fkey'
            ) THEN
                ALTER TABLE rutina_item
                ADD CONSTRAINT rutina_item_ejercicio_id_fkey
                FOREIGN KEY (ejercicio_id) REFERENCES ejercicio(id);
            END IF;
        END$$;
        """))

        db.session.commit()
        return "COLUMNA/FOREIGN KEY OK ✔", 200
    except Exception as e:
        db.session.rollback()
        return f"ERROR aplicando parche: {e}", 500

# =============================================================
# HEALTHCHECK
# =============================================================
@main_bp.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})
