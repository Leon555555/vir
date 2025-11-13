# app/routes.py
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
    """Lunes como inicio de semana."""
    return d - timedelta(days=d.weekday())


def week_dates(center: date | None = None) -> List[date]:
    base = center or date.today()
    start = start_of_week(base)
    return [start + timedelta(days=i) for i in range(7)]


def month_dates(year: int, month: int) -> List[date]:
    """Todas las fechas (1..último) del mes."""
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
# Serializadores simples (para evitar errores JSON)
# =============================================================================
def serialize_user(u: User) -> Dict[str, Any]:
    return {
        "id": u.id,
        "nombre": getattr(u, "nombre", "") or "",
        "email": getattr(u, "email", "") or "",
        "grupo": getattr(u, "grupo", "") or "",
    }


def serialize_rutina(r: Rutina) -> Dict[str, Any]:
    return {
        "id": r.id,
        "nombre": getattr(r, "nombre", "") or "",
        "tipo": (getattr(r, "tipo", "") or "").lower(),
        "descripcion": getattr(r, "descripcion", "") or "",
        "created_by": getattr(r, "created_by", None),
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


# =============================================================================
# Perfil (Atleta)
# =============================================================================
@main_bp.route("/perfil")
@login_required
def perfil_redirect():
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))


main_bp.add_url_rule("/perfil", endpoint="perfil", view_func=perfil_redirect)


@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id: int):
    try:
        if db.session.is_active:
            db.session.rollback()

        user = User.query.get_or_404(user_id)

        # Seguridad: solo admin o el propio usuario
        if current_user.email != "admin@vir.app" and current_user.id != user.id:
            flash("Acceso denegado a perfil ajeno.", "danger")
            return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

        # Semana actual
        fechas = week_dates()
        planes_db = DiaPlan.query.filter(
            DiaPlan.user_id == user.id,
            DiaPlan.fecha.in_(fechas),
        ).all()
        planes = {p.fecha: p for p in planes_db}

        # Aseguramos que todos los días de la semana existan
        for f in fechas:
            if f not in planes:
                nuevo = DiaPlan(user_id=user.id, fecha=f, plan_type="descanso")
                db.session.add(nuevo)
                planes[f] = nuevo
        db.session.commit()

        labels = [f.strftime("%d/%m") for f in fechas]
        propuesto = [planes[f].propuesto_score or 0 for f in fechas]
        realizado = [planes[f].realizado_score or 0 for f in fechas]

        # Rutinas disponibles (para el panel lateral y drag & drop)
        try:
            rutinas = Rutina.query.order_by(Rutina.id.desc()).limit(50).all()
        except Exception:
            db.session.rollback()
            rutinas = []

        semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"

        # ⚠️ IMPORTANTE: 'hoy' para el calendario mensual en perfil.html
        hoy = date.today()

        return render_template(
            "perfil.html",
            user=user,
            fechas=fechas,
            planes=planes,
            labels=labels,
            propuesto=propuesto,
            realizado=realizado,
            rutinas=rutinas,
            semana_str=semana_str,
            hoy=hoy,
        )
    except InternalError:
        db.session.rollback()
        flash("⚠️ Error temporal con la base de datos.", "warning")
        return redirect(url_for("main.index"))


@main_bp.route("/dia/save", methods=["POST"])
@login_required
def save_day():
    user_id = int(request.form["user_id"])
    if current_user.email != "admin@vir.app" and current_user.id != user_id:
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil_redirect"))

    fecha = safe_parse_ymd(request.form["fecha"].strip(), fallback=date.today())
    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha)
        db.session.add(plan)

    plan.plan_type = request.form.get("plan_type", "descanso")
    plan.warmup = request.form.get("warmup", "")
    plan.main = request.form.get("main", "")
    plan.finisher = request.form.get("finisher", "")
    plan.propuesto_score = int(request.form.get("propuesto_score", 0) or 0)
    plan.realizado_score = int(request.form.get("realizado_score", 0) or 0)

    db.session.commit()
    flash("✅ Día actualizado correctamente.", "success")
    return redirect(url_for("main.perfil_usuario", user_id=user_id))


# =============================================================================
# Dashboard Entrenador
# =============================================================================
@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil_redirect"))

    atletas_db = User.query.filter(User.email != "admin@vir.app").all()
    rutinas_db = Rutina.query.order_by(Rutina.id.desc()).all()
    hoy = date.today()

    atletas = [serialize_user(a) for a in atletas_db]
    rutinas = [serialize_rutina(r) for r in rutinas_db]

    return render_template(
        "dashboard_entrenador.html",
        atletas=atletas,
        rutinas=rutinas,
        hoy=hoy,
    )


# =============================================================================
# Bloques / Rutinas → DiaPlan (drag & drop)
# =============================================================================
@main_bp.route("/asignar_bloque", methods=["POST"])
@login_required
def asignar_bloque():
    """Asignar una rutina a un día concreto de un atleta (desde drag&drop)."""
    if current_user.email != "admin@vir.app":
        return jsonify({"status": "error", "msg": "Acceso denegado"}), 403

    data = request.get_json() or {}
    atleta_id = data.get("user_id")
    rutina_id = data.get("rutina_id")
    fecha = safe_parse_ymd(data.get("fecha", ""), fallback=None)

    if not (atleta_id and rutina_id and fecha):
        return jsonify({"status": "error", "msg": "Faltan datos"}), 400

    rutina = Rutina.query.get(rutina_id)
    if not rutina:
        return jsonify({"status": "error", "msg": "Rutina no encontrada"}), 404

    plan = DiaPlan.query.filter_by(user_id=atleta_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=atleta_id, fecha=fecha)
        db.session.add(plan)

    plan.plan_type = (rutina.tipo or "fuerza").lower()
    plan.main = rutina.descripcion or ""
    db.session.commit()

    return jsonify({"status": "ok", "msg": "Bloque asignado", "plan": serialize_plan(plan)})


# =============================================================================
# API y administración (JSON)
# =============================================================================
@main_bp.route("/api/atletas")
@login_required
def api_atletas():
    if current_user.email != "admin@vir.app":
        return jsonify([])
    atletas = User.query.filter(User.email != "admin@vir.app").all()
    return jsonify([serialize_user(a) for a in atletas])


@main_bp.route("/api/rutinas")
@login_required
def api_rutinas():
    if current_user.email != "admin@vir.app":
        return jsonify([])
    rutinas = Rutina.query.order_by(Rutina.id.desc()).all()
    return jsonify([serialize_rutina(r) for r in rutinas])


# =============================================================================
# Administración de usuarios y fixes
# =============================================================================
@main_bp.route("/admin/create_user", methods=["POST"])
@login_required
def admin_create_user():
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil_redirect"))

    nombre = request.form.get("nombre")
    email = (request.form.get("email") or "").lower().strip()
    grupo = request.form.get("grupo", "Atleta")
    password = request.form.get("password")

    if not (nombre and email and password):
        flash("Todos los campos son obligatorios.", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    if User.query.filter_by(email=email).first():
        flash("Ese correo ya existe.", "warning")
        return redirect(url_for("main.dashboard_entrenador"))

    nuevo = User(nombre=nombre, email=email, grupo=grupo)
    nuevo.set_password(password)
    db.session.add(nuevo)
    db.session.commit()
    flash(f"✅ Usuario {nombre} creado correctamente.", "success")
    return redirect(url_for("main.dashboard_entrenador"))


@main_bp.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
def admin_delete_user(user_id: int):
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil_redirect"))

    user = User.query.get_or_404(user_id)
    if user.email == "admin@vir.app":
        flash("No se puede eliminar al admin.", "warning")
        return redirect(url_for("main.dashboard_entrenador"))

    for p in DiaPlan.query.filter_by(user_id=user.id).all():
        db.session.delete(p)
    db.session.delete(user)
    db.session.commit()
    flash(f"🗑️ Usuario {user.nombre} eliminado.", "info")
    return redirect(url_for("main.dashboard_entrenador"))


# =============================================================================
# Crear rutina (usado por partials/rutinas.html)
# =============================================================================
@main_bp.route("/crear_rutina", methods=["POST"])
@login_required
def crear_rutina():
    """
    Permite crear rutinas desde el perfil de atleta o desde el panel.
    Debe corresponder con url_for('main.crear_rutina') en partials/rutinas.html.
    """
    es_admin = current_user.email == "admin@vir.app"
    grupo = (getattr(current_user, "grupo", "") or "").lower()
    if not es_admin and grupo != "entrenador":
        flash("No tienes permiso para crear rutinas.", "danger")
        return redirect(url_for("main.perfil_redirect"))

    nombre = (request.form.get("nombre") or "").strip()
    tipo = (request.form.get("tipo") or "").strip().lower() or "fuerza"
    descripcion = (request.form.get("descripcion") or "").strip()

    if not nombre:
        flash("El nombre de la rutina es obligatorio.", "warning")
        return redirect(request.referrer or url_for("main.dashboard_entrenador"))

    nueva = Rutina(
        nombre=nombre,
        tipo=tipo,
        descripcion=descripcion,
        created_by=current_user.id,
    )
    db.session.add(nueva)
    db.session.commit()

    flash(f"✅ Rutina '{nombre}' creada correctamente.", "success")
    return redirect(request.referrer or url_for("main.dashboard_entrenador"))


# =============================================================================
# Setup rápido y fixes de base de datos
# =============================================================================
@main_bp.route("/setup-admin")
def setup_admin():
    admin_email = "admin@vir.app"
    admin_pass = "Admin123"
    if User.query.filter_by(email=admin_email).first():
        return "✅ Admin ya existe."
    nuevo = User(nombre="Admin ViR", email=admin_email, grupo="Entrenador")
    nuevo.set_password(admin_pass)
    db.session.add(nuevo)
    db.session.commit()
    return f"✅ Admin creado.<br>Email: {admin_email}<br>Contraseña: {admin_pass}"


@main_bp.route("/fix-db")
def fix_db():
    try:
        db.session.execute(
            text(
                """
            ALTER TABLE rutina
            ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """
            )
        )
        db.session.commit()
        return "✅ Fix aplicado."
    except Exception as e:
        db.session.rollback()
        return f"❌ Error: {str(e)}"


@main_bp.route("/reset_admin")
def reset_admin():
    try:
        admin_email = "admin@vir.app"
        admin_pass = "admin123"
        admin = User.query.filter_by(email=admin_email).first()
        if admin:
            admin.set_password(admin_pass)
        else:
            nuevo = User(nombre="Admin ViR", email=admin_email, grupo="Entrenador")
            nuevo.set_password(admin_pass)
            db.session.add(nuevo)
        db.session.commit()
        return f"<b>Admin:</b> {admin_email}<br><b>Pass:</b> {admin_pass}"
    except Exception as e:
        db.session.rollback()
        return f"❌ Error al resetear: {str(e)}"


# =============================================================================
# Otros endpoints
# =============================================================================
@main_bp.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})
