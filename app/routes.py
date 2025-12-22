# app/routes.py
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from calendar import monthrange
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

import requests
from werkzeug.utils import secure_filename

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import text

from app.extensions import db
from app.models import (
    User, DiaPlan, Rutina, Ejercicio, RutinaItem,
    AthleteLog, AthleteCheck, IntegrationAccount
)

# =============================================================
# BLUEPRINTS
# =============================================================
main_bp = Blueprint("main", __name__)
strava_bp = Blueprint("strava", __name__, url_prefix="/strava")

# =============================================================
# HELPERS
# =============================================================
ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v"}


def admin_ok() -> bool:
    return bool(current_user.is_authenticated and getattr(current_user, "is_admin", False))


@main_bp.app_context_processor
def inject_admin():
    return {"admin_ok": admin_ok()}


def start_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_dates(center: Optional[date] = None) -> List[date]:
    base = center or date.today()
    start = start_of_week(base)
    return [start + timedelta(days=i) for i in range(7)]


def safe_parse_ymd(s: str, fallback: Optional[date] = None) -> date:
    if fallback is None:
        fallback = date.today()
    try:
        return datetime.strptime((s or "").strip(), "%Y-%m-%d").date()
    except Exception:
        return fallback


def month_grid(year: int, month: int) -> List[List[Optional[date]]]:
    first_wd, days_in_month = monthrange(year, month)  # 0=lunes
    day = 1
    grid: List[List[Optional[date]]] = []
    week: List[Optional[date]] = [None] * 7

    col = first_wd
    while day <= days_in_month:
        for c in range(col, 7):
            if day > days_in_month:
                break
            week[c] = date(year, month, day)
            day += 1
        grid.append(week)
        week = [None] * 7
        col = 0

    return grid


def ensure_week_plans(user_id: int, fechas: List[date]) -> Dict[date, DiaPlan]:
    existing = DiaPlan.query.filter(
        DiaPlan.user_id == user_id,
        DiaPlan.fecha >= fechas[0],
        DiaPlan.fecha <= fechas[-1],
    ).all()
    by_date = {p.fecha: p for p in existing}
    for f in fechas:
        if f not in by_date:
            p = DiaPlan(user_id=user_id, fecha=f, plan_type="Descanso")
            db.session.add(p)
            by_date[f] = p
    db.session.commit()
    return by_date


def videos_dir() -> str:
    folder = os.path.join(current_app.static_folder, "videos")
    os.makedirs(folder, exist_ok=True)
    return folder


def list_repo_videos() -> List[str]:
    folder = videos_dir()
    out: List[str] = []
    try:
        for name in os.listdir(folder):
            p = os.path.join(folder, name)
            if not os.path.isfile(p):
                continue
            ext = os.path.splitext(name.lower())[1]
            if ext in ALLOWED_VIDEO_EXT:
                out.append(name)
    except FileNotFoundError:
        pass
    out.sort()
    return out


def save_video_to_static(file_storage) -> str:
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValueError("Archivo inválido")

    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_VIDEO_EXT:
        raise ValueError(f"Extensión no permitida ({ext}). Permitidas: {', '.join(sorted(ALLOWED_VIDEO_EXT))}")

    folder = videos_dir()
    dest = os.path.join(folder, filename)

    if os.path.exists(dest):
        base, ext2 = os.path.splitext(filename)
        filename = f"{base}_{int(datetime.utcnow().timestamp())}{ext2}"
        dest = os.path.join(folder, filename)

    file_storage.save(dest)
    return filename


def _set_if_attr(obj, key: str, value):
    if hasattr(obj, key):
        setattr(obj, key, value)


# =============================================================
# DB FIX (TABATA PRESET) - SEGURO
# =============================================================
@main_bp.route("/admin/db_fix_tabata")
@login_required
def admin_db_fix_tabata():
    """
    Fix puntual para Render: crea la columna rutinas.tabata_preset si falta.
    Seguridad:
    - Solo admin
    - Si ya está creada, responde OK y listo
    """
    if not admin_ok():
        return "Acceso denegado", 403

    try:
        db.session.execute(text("""
            ALTER TABLE rutinas
            ADD COLUMN IF NOT EXISTS tabata_preset JSONB;
        """))
        db.session.commit()
        return "OK: columna tabata_preset creada"
    except Exception as e:
        db.session.rollback()
        return f"ERROR: {str(e)}", 500


# =============================================================
# AUTH
# =============================================================
@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.perfil_redirect"))
    return redirect(url_for("main.login"))


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "").strip()

        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(password):
            flash("Credenciales incorrectas", "danger")
            return render_template("login.html")

        login_user(u)
        return redirect(url_for("main.perfil_redirect"))

    return render_template("login.html")


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


# =============================================================
# PERFIL REDIRECT
# =============================================================
@main_bp.route("/perfil")
@login_required
def perfil_redirect():
    if admin_ok():
        return redirect(url_for("main.dashboard_entrenador"))
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id, view="today"))


# =============================================================
# PERFIL USUARIO (ATLETA)
# =============================================================
@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id: int):
    if not (admin_ok() or current_user.id == user_id):
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    user = User.query.get_or_404(user_id)
    view = (request.args.get("view") or "today").strip()

    center_str = (request.args.get("center") or "").strip()
    center = safe_parse_ymd(center_str, fallback=date.today())

    hoy = date.today()

    strava_account = getattr(user, "strava_account", None)

    week_goal = 5

    fechas_semana = week_dates(hoy)
    done_week = set()
    logs_week = AthleteLog.query.filter(
        AthleteLog.user_id == user.id,
        AthleteLog.fecha >= fechas_semana[0],
        AthleteLog.fecha <= fechas_semana[-1],
        AthleteLog.did_train.is_(True),
    ).all()
    for l in logs_week:
        done_week.add(l.fecha)

    week_done = len(done_week)
    streak = week_done  # simple

    plan_hoy = DiaPlan.query.filter_by(user_id=user.id, fecha=hoy).first()
    if not plan_hoy:
        plan_hoy = DiaPlan(user_id=user.id, fecha=hoy, plan_type="Descanso")
        db.session.add(plan_hoy)
        db.session.commit()

    # WEEK VIEW
    fechas: List[date] = []
    planes: Dict[date, DiaPlan] = {}
    semana_str = ""
    if view == "week":
        fechas = week_dates(center)
        semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"
        planes = ensure_week_plans(user.id, fechas)

    # MONTH VIEW
    month_label = ""
    grid: List[List[Optional[date]]] = []
    planes_mes: Dict[date, DiaPlan] = {}
    if view == "month":
        y, m = center.year, center.month
        month_label = center.strftime("%B %Y").capitalize()
        grid = month_grid(y, m)

        start = date(y, m, 1)
        end = date(y, m, monthrange(y, m)[1])
        month_plans = DiaPlan.query.filter(
            DiaPlan.user_id == user.id,
            DiaPlan.fecha >= start,
            DiaPlan.fecha <= end,
        ).all()
        planes_mes = {p.fecha: p for p in month_plans}

        for w in grid:
            for d in w:
                if d and d not in planes_mes:
                    p = DiaPlan(user_id=user.id, fecha=d, plan_type="Descanso")
                    db.session.add(p)
                    planes_mes[d] = p
        db.session.commit()

    return render_template(
        "perfil.html",
        user=user,
        view=view,
        hoy=hoy,
        center=center,

        plan_hoy=plan_hoy,
        streak=streak,
        week_done=week_done,
        week_goal=week_goal,
        done_week=done_week,

        fechas=fechas,
        planes=planes,
        semana_str=semana_str,

        month_label=month_label,
        month_grid=grid,
        planes_mes=planes_mes,

        strava_account=strava_account,
    )


# =============================================================
# PANEL ENTRENADOR
# =============================================================
@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if not admin_ok():
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


@main_bp.route("/dashboard_entrenador")
@login_required
def dashboard_entrenador_alias():
    return dashboard_entrenador()


@main_bp.route("/coach/planificador")
@login_required
def coach_planificador():
    if not admin_ok():
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

    center = safe_parse_ymd(request.args.get("center", ""), fallback=date.today())
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
    if not admin_ok():
        flash("Solo el admin puede editar entrenamientos", "danger")
        return redirect(url_for("main.perfil_redirect"))

    user_id = int(request.form["user_id"])
    fecha = safe_parse_ymd(request.form["fecha"])

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha)
        db.session.add(plan)

    if getattr(plan, "puede_entrenar", "si") == "no":
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


# =============================================================
# ADMIN CRUD
# =============================================================
@main_bp.route("/admin/atletas/nuevo", methods=["POST"])
@login_required
def admin_nuevo_atleta():
    if not admin_ok():
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


@main_bp.route("/crear_rutina", methods=["POST"])
@login_required
def crear_rutina():
    if not admin_ok():
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


@main_bp.route("/admin/ejercicios/nuevo", methods=["POST"])
@login_required
def admin_nuevo_ejercicio():
    if not admin_ok():
        flash("Solo el admin puede crear ejercicios", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    nombre = (request.form.get("nombre") or "").strip()
    categoria = (request.form.get("categoria") or "").strip()
    descripcion = (request.form.get("descripcion") or "").strip()

    selected = (request.form.get("video_existing") or "").strip()
    file = request.files.get("video")

    if not nombre:
        flash("Falta el nombre del ejercicio", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    video_filename = ""

    if selected:
        if selected not in list_repo_videos():
            flash("Ese archivo no existe en /static/videos (subilo al repo primero).", "danger")
            return redirect(url_for("main.dashboard_entrenador"))
        video_filename = selected

    elif file and file.filename:
        try:
            video_filename = save_video_to_static(file)
            flash("⚠️ Video subido al server (en Render gratis puede perderse). Ideal: seleccionar existente.", "warning")
        except Exception as e:
            flash(f"Error subiendo video: {e}", "danger")
            return redirect(url_for("main.dashboard_entrenador"))
    else:
        flash("Falta video: seleccioná uno existente o subí uno.", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    ejercicio = Ejercicio(
        nombre=nombre,
        categoria=categoria,
        descripcion=descripcion,
        video_filename=video_filename
    )
    db.session.add(ejercicio)
    db.session.commit()

    flash("✅ Ejercicio creado en el banco", "success")
    return redirect(url_for("main.dashboard_entrenador"))


@main_bp.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
def admin_delete_user(user_id: int):
    if not admin_ok():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    user = User.query.get_or_404(user_id)
    if user.email == "admin@vir.app":
        flash("No se puede eliminar admin", "warning")
        return redirect(url_for("main.dashboard_entrenador"))

    DiaPlan.query.filter_by(user_id=user.id).delete()
    AthleteLog.query.filter_by(user_id=user.id).delete()
    AthleteCheck.query.filter_by(user_id=user.id).delete()
    IntegrationAccount.query.filter_by(user_id=user.id).delete()

    db.session.delete(user)
    db.session.commit()

    flash("✅ Atleta eliminado", "success")
    return redirect(url_for("main.dashboard_entrenador"))


# =============================================================
# API: DAY DETAIL (MODAL + TABATA)
# =============================================================
@main_bp.route("/api/day_detail")
@login_required
def api_day_detail():
    user_id = request.args.get("user_id", type=int)
    fecha_str = request.args.get("fecha", type=str)

    if not user_id or not fecha_str:
        return jsonify({"ok": False, "error": "Faltan parámetros"}), 400

    if not (admin_ok() or current_user.id == user_id):
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403

    fecha = safe_parse_ymd(fecha_str, fallback=date.today())

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha, plan_type="Descanso")
        db.session.add(plan)
        db.session.commit()

    log = AthleteLog.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not log:
        log = AthleteLog(user_id=user_id, fecha=fecha, did_train=False)
        db.session.add(log)
        db.session.commit()

    checks = AthleteCheck.query.filter_by(user_id=user_id, fecha=fecha, done=True).all()
    done_ids = [c.rutina_item_id for c in checks]

    rutina = None
    items_payload: List[Dict[str, Any]] = []
    is_tabata = False
    tabata_cfg = None

    if (plan.plan_type or "").lower() == "fuerza":
        rid = None
        try:
            rid = int((plan.main or "").strip())
        except Exception:
            rid = None

        if rid:
            rutina = Rutina.query.get(rid)
        else:
            if plan.main:
                rutina = Rutina.query.filter(Rutina.nombre == plan.main).first()

        if rutina:
            preset = getattr(rutina, "tabata_preset", None)
            if preset:
                is_tabata = True
                tabata_cfg = preset

            ritems = (
                RutinaItem.query.filter_by(rutina_id=rutina.id)
                .order_by(RutinaItem.posicion.asc(), RutinaItem.id.asc())
                .all()
            )

            for it in ritems:
                video_src = ""
                if getattr(it, "video_url", None):
                    video_src = it.video_url
                elif it.ejercicio and getattr(it.ejercicio, "video_filename", None):
                    video_src = url_for("static", filename=f"videos/{it.ejercicio.video_filename}")

                items_payload.append({
                    "id": it.id,
                    "nombre": it.nombre,
                    "series": it.series,
                    "reps": it.reps,
                    "descanso": it.descanso,
                    "video_src": video_src,
                })

    return jsonify({
        "ok": True,
        "plan": {
            "plan_type": plan.plan_type,
            "warmup": plan.warmup,
            "main": plan.main,
            "finisher": plan.finisher,
            "puede_entrenar": plan.puede_entrenar,
            "comentario_atleta": plan.comentario_atleta,
        },
        "rutina": ({"id": rutina.id, "nombre": rutina.nombre} if rutina else None),
        "items": items_payload,
        "checks": done_ids,
        "log": {
            "did_train": bool(log.did_train),
            "warmup_done": log.warmup_done,
            "main_done": log.main_done,
            "finisher_done": log.finisher_done,
        },
        "is_tabata": bool(is_tabata),
        "tabata_cfg": tabata_cfg,
    })


@main_bp.route("/athlete/check_item", methods=["POST"])
@login_required
def athlete_check_item():
    user_id = request.form.get("user_id", type=int)
    fecha_str = request.form.get("fecha", type=str)
    item_id = request.form.get("item_id", type=int)
    done = (request.form.get("done") or "0") == "1"

    if not user_id or not fecha_str or not item_id:
        return jsonify({"ok": False, "error": "Faltan datos"}), 400

    if not (admin_ok() or current_user.id == user_id):
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403

    fecha = safe_parse_ymd(fecha_str, fallback=date.today())

    row = AthleteCheck.query.filter_by(user_id=user_id, fecha=fecha, rutina_item_id=item_id).first()
    if not row:
        row = AthleteCheck(user_id=user_id, fecha=fecha, rutina_item_id=item_id, done=done)
        db.session.add(row)
    else:
        row.done = done

    _set_if_attr(row, "updated_at", datetime.utcnow())
    db.session.commit()
    return jsonify({"ok": True})


@main_bp.route("/athlete/save_log", methods=["POST"])
@login_required
def athlete_save_log():
    data = request.get_json(silent=True) or {}

    user_id = int(data.get("user_id") or 0)
    fecha_str = (data.get("fecha") or "").strip()

    if not user_id or not fecha_str:
        return jsonify({"ok": False, "error": "Faltan datos"}), 400

    if not (admin_ok() or current_user.id == user_id):
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403

    fecha = safe_parse_ymd(fecha_str, fallback=date.today())

    log = AthleteLog.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not log:
        log = AthleteLog(user_id=user_id, fecha=fecha)
        db.session.add(log)

    log.did_train = bool(data.get("did_train"))
    log.warmup_done = data.get("warmup_done") or ""
    log.main_done = data.get("main_done") or ""
    log.finisher_done = data.get("finisher_done") or ""
    _set_if_attr(log, "updated_at", datetime.utcnow())

    db.session.commit()
    return jsonify({"ok": True})


@main_bp.route("/athlete/save_availability", methods=["POST"])
@login_required
def athlete_save_availability():
    data = request.get_json(silent=True) or {}

    user_id = int(data.get("user_id") or 0)
    fecha_str = (data.get("fecha") or "").strip()
    no_puedo = bool(data.get("no_puedo"))
    comentario = (data.get("comentario") or "").strip()

    if not user_id or not fecha_str:
        return jsonify({"ok": False, "error": "Faltan datos"}), 400

    if not (admin_ok() or current_user.id == user_id):
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403

    fecha = safe_parse_ymd(fecha_str, fallback=date.today())

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha, plan_type="Descanso")
        db.session.add(plan)

    plan.puede_entrenar = "no" if no_puedo else "si"
    plan.comentario_atleta = comentario
    db.session.commit()

    return jsonify({"ok": True})


# =============================================================
# AI: session script
# =============================================================
@main_bp.route("/ai/session_script", methods=["POST"])
@login_required
def ai_session_script():
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id") or 0)
    fecha_str = (data.get("fecha") or "").strip()

    if not user_id or not fecha_str:
        return jsonify({"ok": False, "error": "Faltan datos"}), 400

    if not (admin_ok() or current_user.id == user_id):
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403

    fecha = safe_parse_ymd(fecha_str, fallback=date.today())
    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        return jsonify({"ok": True, "script": "Día sin plan. Recuperación y movilidad suave 20–30’."})

    lines: List[str] = []
    lines.append(f"📅 {fecha.strftime('%d/%m/%Y')} · {plan.plan_type or 'Entreno'}")
    lines.append("")
    if plan.warmup:
        lines.append("🔥 Activación")
        lines.append(plan.warmup.strip())
        lines.append("")
    if plan.main:
        lines.append("💪 Bloque principal")
        lines.append(plan.main.strip())
        lines.append("")
    if plan.finisher:
        lines.append("🧊 Enfriamiento")
        lines.append(plan.finisher.strip())
        lines.append("")
    lines.append("✅ Tip: hidratación + 5’ de respiración al final.")

    return jsonify({"ok": True, "script": "\n".join(lines)})


# =============================================================
# STRAVA OAUTH (REAL)
# =============================================================
@strava_bp.route("/connect", endpoint="connect")
@login_required
def strava_connect():
    client_id = os.getenv("STRAVA_CLIENT_ID", "").strip()
    redirect_uri = os.getenv("STRAVA_REDIRECT_URI", "").strip()

    if not client_id or not redirect_uri:
        flash("Strava no está configurado (faltan STRAVA_CLIENT_ID / STRAVA_REDIRECT_URI).", "warning")
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "approval_prompt": "auto",
        "scope": "read,activity:read_all",
    }
    return redirect("https://www.strava.com/oauth/authorize?" + urlencode(params))


@strava_bp.route("/callback", endpoint="callback")
@login_required
def strava_callback():
    code = (request.args.get("code") or "").strip()
    if not code:
        flash("Strava: no llegó el code.", "danger")
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

    client_id = os.getenv("STRAVA_CLIENT_ID", "").strip()
    client_secret = os.getenv("STRAVA_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        flash("Strava: falta STRAVA_CLIENT_ID o STRAVA_CLIENT_SECRET.", "danger")
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

    try:
        resp = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=20,
        )
        data = resp.json()
    except Exception as e:
        flash(f"Strava: error conectando con Strava ({e}).", "danger")
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

    if "access_token" not in data:
        flash("Strava: respuesta inválida al pedir token.", "danger")
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_at = data.get("expires_at")
    athlete = data.get("athlete") or {}
    external_user_id = str(athlete.get("id") or "")

    acct = IntegrationAccount.query.filter_by(user_id=current_user.id, provider="strava").first()
    if not acct:
        acct = IntegrationAccount(user_id=current_user.id, provider="strava")
        db.session.add(acct)

    _set_if_attr(acct, "access_token", access_token)
    _set_if_attr(acct, "refresh_token", refresh_token)
    _set_if_attr(acct, "expires_at", expires_at)
    _set_if_attr(acct, "external_user_id", external_user_id)
    _set_if_attr(acct, "updated_at", datetime.utcnow())

    db.session.commit()

    flash("✅ Strava conectado correctamente.", "success")
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))
