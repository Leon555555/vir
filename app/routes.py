# app/routes.py
from __future__ import annotations

from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import Any, Dict, List, Tuple, Optional

import os
import secrets
import string
from werkzeug.utils import secure_filename

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, current_app
)
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import (
    User, DiaPlan, Rutina, Ejercicio, RutinaItem,
    AthleteCheck, AthleteLog
)

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
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            return fallback or date.today()

def is_admin() -> bool:
    return bool(
        current_user.is_authenticated and (
            getattr(current_user, "is_admin", False) or current_user.email == "admin@vir.app"
        )
    )

@main_bp.app_context_processor
def inject_is_admin():
    return {"is_admin": is_admin, "admin_ok": is_admin()}


# =============================================================
# SERIALIZADORES
# =============================================================
def serialize_user(u: User) -> Dict[str, Any]:
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "grupo": u.grupo or ""}

def serialize_rutina(r: Rutina) -> Dict[str, Any]:
    return {
        "id": r.id,
        "nombre": r.nombre,
        "tipo": getattr(r, "tipo", "") or "",
        "descripcion": getattr(r, "descripcion", "") or "",
        "created_by": getattr(r, "created_by", None),
    }

def serialize_plan(p: DiaPlan) -> Dict[str, Any]:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "fecha": p.fecha.strftime("%Y-%m-%d"),
        "plan_type": (p.plan_type or "Descanso"),
        "warmup": p.warmup or "",
        "main": p.main or "",
        "finisher": p.finisher or "",
        "propuesto_score": p.propuesto_score or 0,
        "realizado_score": p.realizado_score or 0,
        "puede_entrenar": (getattr(p, "puede_entrenar", None) or "si"),
        "comentario_atleta": (getattr(p, "comentario_atleta", None) or ""),
    }


# =============================================================
# HELPERS PERFIL (PROGRESO / RACHAS)
# =============================================================
def ensure_week_plans(user_id: int, fechas: List[date]) -> Dict[date, DiaPlan]:
    planes_db = DiaPlan.query.filter(
        DiaPlan.user_id == user_id,
        DiaPlan.fecha.in_(fechas)
    ).all()
    planes = {p.fecha: p for p in planes_db}

    changed = False
    for f in fechas:
        if f not in planes:
            nuevo = DiaPlan(user_id=user_id, fecha=f, plan_type="Descanso")
            planes[f] = nuevo
            db.session.add(nuevo)
            changed = True
    if changed:
        db.session.commit()
    return planes

def get_strength_done_days(user_id: int, fechas: List[date]) -> set[date]:
    """Día fuerza 'done' si todos los items de la rutina del día están hechos."""
    done_days: set[date] = set()
    plans = DiaPlan.query.filter(DiaPlan.user_id == user_id, DiaPlan.fecha.in_(fechas)).all()
    plans_by_date = {p.fecha: p for p in plans}

    for f in fechas:
        p = plans_by_date.get(f)
        if not p:
            continue
        if (p.plan_type or "").lower() != "fuerza":
            continue
        if not (p.main and isinstance(p.main, str) and p.main.startswith("RUTINA:")):
            continue

        rid_str = p.main.split(":", 1)[1].strip()
        if not rid_str.isdigit():
            continue
        rid = int(rid_str)
        items = RutinaItem.query.filter_by(rutina_id=rid).all()
        if not items:
            continue

        checks = AthleteCheck.query.filter(
            AthleteCheck.user_id == user_id,
            AthleteCheck.fecha == f,
            AthleteCheck.rutina_item_id.in_([it.id for it in items])
        ).all()
        done_ids = {c.rutina_item_id for c in checks if c.done}
        if len(done_ids) == len(items):
            done_days.add(f)

    return done_days

def get_log_done_days(user_id: int, fechas: List[date]) -> set[date]:
    logs = AthleteLog.query.filter(
        AthleteLog.user_id == user_id,
        AthleteLog.fecha.in_(fechas),
        AthleteLog.did_train == True
    ).all()
    return {l.fecha for l in logs}

def compute_streak(user_id: int) -> int:
    """Racha: días consecutivos hacia atrás donde el usuario entrenó (log.did_train) o completó fuerza."""
    today = date.today()
    streak = 0

    for i in range(0, 365):
        d = today - timedelta(days=i)
        # criterio "hecho"
        log = AthleteLog.query.filter_by(user_id=user_id, fecha=d).first()
        if log and log.did_train:
            streak += 1
            continue

        # fuerza: completo si todos checks del día están hechos
        plan = DiaPlan.query.filter_by(user_id=user_id, fecha=d).first()
        if plan and (plan.plan_type or "").lower() == "fuerza" and plan.main and isinstance(plan.main, str) and plan.main.startswith("RUTINA:"):
            rid_str = plan.main.split(":", 1)[1].strip()
            if rid_str.isdigit():
                rid = int(rid_str)
                items = RutinaItem.query.filter_by(rutina_id=rid).all()
                if items:
                    checks = AthleteCheck.query.filter(
                        AthleteCheck.user_id == user_id,
                        AthleteCheck.fecha == d,
                        AthleteCheck.rutina_item_id.in_([it.id for it in items])
                    ).all()
                    done_ids = {c.rutina_item_id for c in checks if c.done}
                    if len(done_ids) == len(items):
                        streak += 1
                        continue

        # si no está hecho, se corta
        break

    return streak

def week_goal_and_done(user_id: int, fechas: List[date], planes: Dict[date, DiaPlan]) -> Tuple[int, int]:
    """Goal = cantidad de días no descanso, done = días completados (log o fuerza completa)"""
    goal = 0
    for f in fechas:
        p = planes.get(f)
        if not p:
            continue
        if (p.plan_type or "").lower() != "descanso":
            goal += 1

    done_days = get_strength_done_days(user_id, fechas).union(get_log_done_days(user_id, fechas))
    return goal, len(done_days)


# =============================================================
# HOME / LOGIN
# =============================================================
@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if is_admin():
            return redirect(url_for("main.dashboard_entrenador"))
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))
    return redirect(url_for("main.login"))

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Bienvenido {user.nombre}", "success")
            if is_admin():
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

@main_bp.route("/perfil")
@login_required
def perfil_redirect():
    if is_admin():
        return redirect(url_for("main.dashboard_entrenador"))
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))


# =============================================================
# PERFIL (ATLETA) - HOY / SEMANA / MES / PROGRESO
# =============================================================
@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id: int):
    user = User.query.get_or_404(user_id)

    if (not is_admin()) and current_user.id != user.id:
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

    view = (request.args.get("view") or "today").strip().lower()  # today/week/month/progress
    center = safe_parse_ymd(request.args.get("center", ""), fallback=date.today())
    hoy = date.today()

    # HOY plan
    plan_hoy = DiaPlan.query.filter_by(user_id=user.id, fecha=hoy).first()
    if not plan_hoy:
        plan_hoy = DiaPlan(user_id=user.id, fecha=hoy, plan_type="Descanso")
        db.session.add(plan_hoy)
        db.session.commit()

    # Semana
    fechas = week_dates(center)
    planes = ensure_week_plans(user.id, fechas)
    semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"

    done_week = get_strength_done_days(user.id, fechas).union(get_log_done_days(user.id, fechas))

    # Mes
    dias_mes = month_dates(center.year, center.month)
    planes_mes_db = DiaPlan.query.filter(
        DiaPlan.user_id == user.id,
        DiaPlan.fecha.in_(dias_mes)
    ).all()
    planes_mes = {p.fecha: p for p in planes_mes_db}

    changed = False
    for d in dias_mes:
        if d not in planes_mes:
            nuevo = DiaPlan(user_id=user.id, fecha=d, plan_type="Descanso")
            planes_mes[d] = nuevo
            db.session.add(nuevo)
            changed = True
    if changed:
        db.session.commit()

    done_month = get_strength_done_days(user.id, dias_mes).union(get_log_done_days(user.id, dias_mes))

    # Calendario mes (semanas)
    first_day = date(center.year, center.month, 1)
    start = start_of_week(first_day)
    last_day = dias_mes[-1]
    end = start_of_week(last_day) + timedelta(days=6)

    month_grid: List[List[Optional[date]]] = []
    cur = start
    while cur <= end:
        w: List[Optional[date]] = []
        for _ in range(7):
            w.append(cur if cur.month == center.month else None)
            cur += timedelta(days=1)
        month_grid.append(w)

    month_label = first_day.strftime("%B %Y").upper()

    # Rutinas (por si ampliás)
    rutinas = Rutina.query.order_by(Rutina.id.desc()).all()

    # checks semana (para compatibilidad con tu lógica previa)
    done_set: set[Tuple[date, int]] = set()
    checks = AthleteCheck.query.filter(
        AthleteCheck.user_id == user.id,
        AthleteCheck.fecha.in_(fechas)
    ).all()
    for c in checks:
        if c.done:
            done_set.add((c.fecha, c.rutina_item_id))

    # logs semana (compat)
    logs = AthleteLog.query.filter(
        AthleteLog.user_id == user.id,
        AthleteLog.fecha.in_(fechas)
    ).all()
    log_by_day: Dict[date, AthleteLog] = {l.fecha: l for l in logs}

    streak = compute_streak(user.id)
    week_goal, week_done = week_goal_and_done(user.id, fechas, planes)

    return render_template(
        "perfil.html",
        user=user,
        view=view,

        hoy=hoy,
        plan_hoy=plan_hoy,

        center=center,
        fechas=fechas,
        planes=planes,
        semana_str=semana_str,
        done_week=done_week,

        dias_mes=dias_mes,
        planes_mes=planes_mes,
        done_month=done_month,
        month_grid=month_grid,
        month_label=month_label,

        rutinas=rutinas,
        done_set=done_set,
        log_by_day=log_by_day,

        streak=streak,
        week_goal=week_goal,
        week_done=week_done,
    )


# =============================================================
# API: detalle del día (modal full-screen atleta)
# =============================================================
@main_bp.route("/api/day_detail")
@login_required
def api_day_detail():
    user_id = request.args.get("user_id", type=int)
    fecha = safe_parse_ymd(request.args.get("fecha", ""), fallback=date.today())

    if not user_id:
        return jsonify({"ok": False, "error": "Falta user_id"}), 400
    if (not is_admin()) and current_user.id != user_id:
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha, plan_type="Descanso")
        db.session.add(plan)
        db.session.commit()

    payload: Dict[str, Any] = {
        "ok": True,
        "fecha": fecha.isoformat(),
        "plan": serialize_plan(plan),
        "rutina": None,
        "items": [],
        "checks": [],
        "log": None,
    }

    log = AthleteLog.query.filter_by(user_id=user_id, fecha=fecha).first()
    payload["log"] = {
        "did_train": bool(log.did_train) if log else False,
        "warmup_done": (log.warmup_done or "") if log else "",
        "main_done": (log.main_done or "") if log else "",
        "finisher_done": (log.finisher_done or "") if log else "",
    }

    if plan.main and isinstance(plan.main, str) and plan.main.startswith("RUTINA:"):
        rid_str = plan.main.split(":", 1)[1].strip()
        if rid_str.isdigit():
            rid = int(rid_str)
            r = Rutina.query.get(rid)
            if r:
                items = (
                    RutinaItem.query.filter_by(rutina_id=rid)
                    .order_by(RutinaItem.id.asc()).all()
                )
                payload["rutina"] = serialize_rutina(r)
                payload["items"] = [
                    {
                        "id": it.id,
                        "nombre": it.nombre,
                        "series": it.series or "",
                        "reps": it.reps or "",
                        "descanso": it.descanso or "",
                        "video_url": it.video_url or "",
                        "nota": it.nota or "",
                    }
                    for it in items
                ]

                checks = AthleteCheck.query.filter(
                    AthleteCheck.user_id == user_id,
                    AthleteCheck.fecha == fecha,
                    AthleteCheck.rutina_item_id.in_([it.id for it in items])
                ).all()
                done_ids = {c.rutina_item_id for c in checks if c.done}
                payload["checks"] = list(done_ids)

    return jsonify(payload)


# =============================================================
# CHECK por ejercicio (fuerza)
# =============================================================
@main_bp.route("/athlete/check_item", methods=["POST"])
@login_required
def athlete_check_item():
    try:
        user_id = request.form.get("user_id", type=int)
        fecha = safe_parse_ymd(request.form.get("fecha", ""), fallback=date.today())
        item_id = request.form.get("item_id", type=int)
        done = request.form.get("done", "1") in ("1", "true", "True", "on")

        if not user_id or not item_id:
            return jsonify({"ok": False, "error": "Faltan datos"}), 400
        if (not is_admin()) and current_user.id != user_id:
            return jsonify({"ok": False, "error": "Acceso denegado"}), 403

        item = RutinaItem.query.get_or_404(item_id)

        existing = AthleteCheck.query.filter_by(
            user_id=user_id, fecha=fecha, rutina_item_id=item.id
        ).first()

        if existing:
            existing.done = done
            existing.updated_at = datetime.utcnow()
        else:
            db.session.add(AthleteCheck(
                user_id=user_id,
                fecha=fecha,
                rutina_item_id=item.id,
                done=done,
                updated_at=datetime.utcnow()
            ))

        db.session.commit()
        return jsonify({"ok": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================
# Guardar "lo realizado" + marcar entreno (did_train)
# =============================================================
@main_bp.route("/athlete/save_log", methods=["POST"])
@login_required
def athlete_save_log():
    try:
        data = request.get_json(silent=True) or {}
        user_id = int(data.get("user_id"))
        fecha = safe_parse_ymd(data.get("fecha", ""), fallback=date.today())

        if (not is_admin()) and current_user.id != user_id:
            return jsonify({"ok": False, "error": "Acceso denegado"}), 403

        log = AthleteLog.query.filter_by(user_id=user_id, fecha=fecha).first()
        if not log:
            log = AthleteLog(user_id=user_id, fecha=fecha)
            db.session.add(log)

        log.did_train = bool(data.get("did_train", False))
        log.warmup_done = (data.get("warmup_done") or "").strip()
        log.main_done = (data.get("main_done") or "").strip()
        log.finisher_done = (data.get("finisher_done") or "").strip()
        log.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({"ok": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500


# =============================================================
# DASHBOARD ENTRENADOR (PANEL)
# =============================================================
@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if not is_admin():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutinas = Rutina.query.order_by(Rutina.id.desc()).all()
    ejercicios = Ejercicio.query.order_by(Ejercicio.id.desc()).all()
    atletas = User.query.filter(User.email != "admin@vir.app").order_by(User.id.desc()).all()

    return render_template(
        "panel_entrenador.html",
        rutinas=rutinas,
        ejercicios=ejercicios,
        atletas=atletas,
    )


# =============================================================
# ✅ NUEVO ATLETA (GET/POST) + password inicial
# =============================================================
def _gen_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

@main_bp.route("/admin/nuevo_atleta", methods=["GET", "POST"])
@login_required
def admin_nuevo_atleta():
    if not is_admin():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        grupo = (request.form.get("grupo") or "").strip()

        if not nombre or not email:
            flash("Nombre y email son obligatorios", "danger")
            return render_template("admin_nuevo_atleta.html")

        exists = User.query.filter_by(email=email).first()
        if exists:
            flash("Ya existe un usuario con ese email", "danger")
            return render_template("admin_nuevo_atleta.html")

        raw_pass = _gen_password(10)

        u = User(
            nombre=nombre,
            email=email,
            grupo=grupo or None,
            is_admin=False
        )

        # tu modelo ya tiene esto (lo usás en login)
        u.set_password(raw_pass)

        db.session.add(u)
        db.session.commit()

        flash(f"✅ Atleta creado. Password inicial: {raw_pass}", "success")
        flash("👉 Copiá y pasale esa contraseña al atleta (después la cambiamos).", "info")
        return redirect(url_for("main.dashboard_entrenador"))

    return render_template("admin_nuevo_atleta.html")


# =============================================================
# PLANIFICADOR (SEMANA) - entrenador
# =============================================================
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


# =============================================================
# GUARDAR DÍA (PLANIFICADOR)
# =============================================================
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
# PANEL: CREAR RUTINA
# =============================================================
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


# =============================================================
# PANEL: SUBIR EJERCICIO (BANCO)
# =============================================================
@main_bp.route("/admin/ejercicios/nuevo", methods=["POST"])
@login_required
def admin_nuevo_ejercicio():
    if not is_admin():
        flash("Solo el admin puede crear ejercicios", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    nombre = (request.form.get("nombre") or "").strip()
    categoria = (request.form.get("categoria") or "").strip()
    descripcion = (request.form.get("descripcion") or "").strip()
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
    file.save(os.path.join(upload_folder, filename))

    ejercicio = Ejercicio(
        nombre=nombre,
        categoria=categoria,
        descripcion=descripcion,
        video_filename=filename
    )
    db.session.add(ejercicio)
    db.session.commit()

    flash("✅ Ejercicio subido", "success")
    return redirect(url_for("main.dashboard_entrenador"))


# =============================================================
# PANEL: ELIMINAR ATLETA
# =============================================================
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


# =============================================================
# CRUD rutinas (builder)
# =============================================================
@main_bp.route("/rutinas/<int:rutina_id>/builder")
@login_required
def rutina_builder(rutina_id: int):
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    items = RutinaItem.query.filter_by(rutina_id=rutina.id).order_by(RutinaItem.id).all()
    ejercicios = Ejercicio.query.order_by(Ejercicio.nombre).all()

    return render_template("rutina_builder.html", rutina=rutina, items=items, ejercicios=ejercicios)


@main_bp.route("/rutinas/<int:rutina_id>/add_item", methods=["POST"])
@login_required
def rutina_add_item(rutina_id: int):
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    ejercicio_id = request.form.get("ejercicio_id", type=int)
    if not ejercicio_id:
        flash("Falta el ejercicio a añadir", "danger")
        return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))

    ejercicio = Ejercicio.query.get_or_404(ejercicio_id)

    item = RutinaItem(
        rutina_id=rutina.id,
        ejercicio_id=ejercicio.id,
        nombre=ejercicio.nombre,
        series=(request.form.get("series") or "").strip(),
        reps=(request.form.get("reps") or "").strip(),
        descanso=(request.form.get("descanso") or "").strip(),
        nota=(request.form.get("nota") or "").strip(),
        video_url=f"videos/{ejercicio.video_filename}" if ejercicio.video_filename else ""
    )
    db.session.add(item)
    db.session.commit()

    flash("✅ Ejercicio añadido", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))


@main_bp.route("/rutinas/<int:rutina_id>/items/<int:item_id>/update", methods=["POST"])
@login_required
def rutina_update_item(rutina_id: int, item_id: int):
    """✅ ESTA RUTA FALTABA (tu template la llama)"""
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    item = RutinaItem.query.get_or_404(item_id)
    if item.rutina_id != rutina_id:
        flash("Item no corresponde a la rutina", "danger")
        return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))

    item.series = (request.form.get("series") or "").strip()
    item.reps = (request.form.get("reps") or "").strip()
    item.descanso = (request.form.get("descanso") or "").strip()
    item.nota = (request.form.get("nota") or "").strip()

    db.session.commit()
    flash("✅ Cambios guardados", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))


@main_bp.route("/rutinas/<int:rutina_id>/items/<int:item_id>/delete", methods=["POST"])
@login_required
def rutina_delete_item(rutina_id: int, item_id: int):
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    item = RutinaItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()

    flash("🗑️ Item eliminado", "info")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))


# =============================================================
# HEALTHCHECK
# =============================================================
@main_bp.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})
