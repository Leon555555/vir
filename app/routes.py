# app/routes.py
from __future__ import annotations

from datetime import date, datetime, timedelta
from calendar import monthrange
from typing import List, Dict, Any

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import and_

from app.extensions import db
from app.models import (
    User, DiaPlan, Rutina, Ejercicio, RutinaItem,
    AthleteLog, AthleteCheck, IntegrationAccount
)

main_bp = Blueprint("main", __name__)


# -------------------------------------------------------------
# HELPERS (fechas)
# -------------------------------------------------------------
def start_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())

def week_dates(center: date | None = None) -> List[date]:
    base = center or date.today()
    start = start_of_week(base)
    return [start + timedelta(days=i) for i in range(7)]

def safe_parse_ymd(s: str, fallback: date | None = None) -> date:
    if fallback is None:
        fallback = date.today()
    try:
        return datetime.strptime((s or "").strip(), "%Y-%m-%d").date()
    except Exception:
        return fallback

def month_grid(year: int, month: int) -> List[List[date | None]]:
    first_wd, days_in_month = monthrange(year, month)  # 0=lunes
    # Alineamos a lunes
    day = 1
    grid: List[List[date | None]] = []
    week: List[date | None] = [None] * 7

    # llenar offset
    col = first_wd
    for _ in range(col):
        week[_] = None

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


def admin_ok() -> bool:
    return bool(current_user.is_authenticated and getattr(current_user, "is_admin", False))


@main_bp.app_context_processor
def inject_admin():
    return {"admin_ok": admin_ok()}


# -------------------------------------------------------------
# AUTH
# -------------------------------------------------------------
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


# -------------------------------------------------------------
# PERFIL REDIRECT
# -------------------------------------------------------------
@main_bp.route("/perfil")
@login_required
def perfil_redirect():
    # Admin va al panel (si tu layout tiene panel)
    if admin_ok():
        # tu coach blueprint expone /coach/dashboard
        return redirect(url_for("coach.dashboard_entrenador"))
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id, view="today"))


# -------------------------------------------------------------
# PERFIL USUARIO (ATLETA)
# -------------------------------------------------------------
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

    # Strava
    strava_account = None
    if user.integration_accounts:
        for acc in user.integration_accounts:
            if (acc.provider or "").lower() == "strava":
                strava_account = acc
                break

    # Objetivos
    week_goal = 5
    # Semana actual
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
    streak = week_done  # simple (si querés, lo hacemos real luego)

    # Plan hoy
    plan_hoy = DiaPlan.query.filter_by(user_id=user.id, fecha=hoy).first()
    if not plan_hoy:
        plan_hoy = DiaPlan(user_id=user.id, fecha=hoy, plan_type="Descanso")
        db.session.add(plan_hoy)
        db.session.commit()

    # WEEK VIEW
    fechas = []
    planes = {}
    semana_str = ""
    if view == "week":
        fechas = week_dates(center)
        semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"
        # asegurar planes
        existing = DiaPlan.query.filter(
            DiaPlan.user_id == user.id,
            DiaPlan.fecha >= fechas[0],
            DiaPlan.fecha <= fechas[-1],
        ).all()
        by_date = {p.fecha: p for p in existing}
        for f in fechas:
            if f not in by_date:
                p = DiaPlan(user_id=user.id, fecha=f, plan_type="Descanso")
                db.session.add(p)
                by_date[f] = p
        db.session.commit()
        planes = by_date

    # MONTH VIEW
    month_label = ""
    grid = []
    planes_mes = {}
    if view == "month":
        y, m = center.year, center.month
        month_label = center.strftime("%B %Y").capitalize()
        grid = month_grid(y, m)

        # fetch all plans in month
        start = date(y, m, 1)
        end = date(y, m, monthrange(y, m)[1])
        month_plans = DiaPlan.query.filter(
            DiaPlan.user_id == user.id,
            DiaPlan.fecha >= start,
            DiaPlan.fecha <= end,
        ).all()
        planes_mes = {p.fecha: p for p in month_plans}

        # asegurar planes
        for week in grid:
            for d in week:
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


# -------------------------------------------------------------
# API: DAY DETAIL (ESTO HACE FUNCIONAR "Empezar" / "Ver detalle")
# -------------------------------------------------------------
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

    # log
    log = AthleteLog.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not log:
        log = AthleteLog(user_id=user_id, fecha=fecha, did_train=False)
        db.session.add(log)
        db.session.commit()

    # checks
    checks = AthleteCheck.query.filter_by(user_id=user_id, fecha=fecha, done=True).all()
    done_ids = [c.rutina_item_id for c in checks]

    # Rutina/items
    rutina = None
    items_payload: List[Dict[str, Any]] = []
    is_tabata = False
    tabata_cfg = None

    # Tu convención: cuando plan_type == fuerza y plan.main tiene "rutina id" o nombre
    if (plan.plan_type or "").lower() == "fuerza":
        # si plan.main guarda un ID numérico
        rid = None
        try:
            rid = int((plan.main or "").strip())
        except Exception:
            rid = None

        if rid:
            rutina = Rutina.query.get(rid)
        else:
            # fallback por nombre exacto
            if plan.main:
                rutina = Rutina.query.filter(Rutina.nombre == plan.main).first()

        if rutina:
            # Tabata: por tipo o por preset
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
                # 1) si el item tiene video_url directo
                if it.video_url:
                    video_src = it.video_url
                # 2) si tiene ejercicio vinculado con filename
                elif it.ejercicio and it.ejercicio.video_filename:
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


# -------------------------------------------------------------
# ATHLETE: CHECK ITEM
# -------------------------------------------------------------
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

    row.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"ok": True})


# -------------------------------------------------------------
# ATHLETE: SAVE LOG
# -------------------------------------------------------------
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
    log.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify({"ok": True})


# -------------------------------------------------------------
# ATHLETE: SAVE AVAILABILITY (bloqueo día)
# -------------------------------------------------------------
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
