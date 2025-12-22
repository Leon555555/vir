# app/routes.py
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from calendar import monthrange
from typing import List, Dict, Any, Optional
from werkzeug.utils import secure_filename

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, current_app
)
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import (
    User, DiaPlan, Rutina, Ejercicio, RutinaItem,
    AthleteLog, AthleteCheck
)

# =============================================================
# BLUEPRINT ÚNICO
# =============================================================
main_bp = Blueprint("main", __name__)

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
    first_wd, days_in_month = monthrange(year, month)
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
    for name in os.listdir(folder):
        p = os.path.join(folder, name)
        if os.path.isfile(p) and os.path.splitext(name.lower())[1] in ALLOWED_VIDEO_EXT:
            out.append(name)
    out.sort()
    return out


def save_video_to_static(file_storage) -> str:
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValueError("Archivo inválido")

    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_VIDEO_EXT:
        raise ValueError("Extensión no permitida")

    folder = videos_dir()
    dest = os.path.join(folder, filename)

    if os.path.exists(dest):
        base, ext2 = os.path.splitext(filename)
        filename = f"{base}_{int(datetime.utcnow().timestamp())}{ext2}"
        dest = os.path.join(folder, filename)

    file_storage.save(dest)
    return filename


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
# PERFIL ATLETA
# =============================================================
@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id: int):
    if not (admin_ok() or current_user.id == user_id):
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    user = User.query.get_or_404(user_id)
    view = (request.args.get("view") or "today").strip()
    center = safe_parse_ymd(request.args.get("center", ""), fallback=date.today())
    hoy = date.today()

    week_goal = 5
    fechas_semana = week_dates(hoy)

    done_week = {
        l.fecha for l in AthleteLog.query.filter(
            AthleteLog.user_id == user.id,
            AthleteLog.fecha >= fechas_semana[0],
            AthleteLog.fecha <= fechas_semana[-1],
            AthleteLog.did_train.is_(True),
        ).all()
    }

    plan_hoy = DiaPlan.query.filter_by(user_id=user.id, fecha=hoy).first()
    if not plan_hoy:
        plan_hoy = DiaPlan(user_id=user.id, fecha=hoy, plan_type="Descanso")
        db.session.add(plan_hoy)
        db.session.commit()

    fechas, planes, semana_str = [], {}, ""
    if view == "week":
        fechas = week_dates(center)
        planes = ensure_week_plans(user.id, fechas)
        semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"

    month_label, grid, planes_mes = "", [], {}
    if view == "month":
        y, m = center.year, center.month
        month_label = center.strftime("%B %Y").capitalize()
        grid = month_grid(y, m)

        start = date(y, m, 1)
        end = date(y, m, monthrange(y, m)[1])
        planes_mes = {
            p.fecha: p for p in DiaPlan.query.filter(
                DiaPlan.user_id == user.id,
                DiaPlan.fecha >= start,
                DiaPlan.fecha <= end,
            ).all()
        }

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
        streak=len(done_week),
        week_done=len(done_week),
        week_goal=week_goal,
        done_week=done_week,
        fechas=fechas,
        planes=planes,
        semana_str=semana_str,
        month_label=month_label,
        month_grid=grid,
        planes_mes=planes_mes,
    )


# =============================================================
# PANEL ENTRENADOR
# =============================================================
@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if not admin_ok():
        return redirect(url_for("main.perfil_redirect"))

    return render_template(
        "panel_entrenador.html",
        atletas=User.query.filter(User.is_admin.is_(False)).all(),
        rutinas=Rutina.query.all(),
        ejercicios=Ejercicio.query.all(),
        available_videos=list_repo_videos(),
    )


# =============================================================
# API DAY DETAIL (TABATA)
# =============================================================
@main_bp.route("/api/day_detail")
@login_required
def api_day_detail():
    user_id = request.args.get("user_id", type=int)
    fecha = safe_parse_ymd(request.args.get("fecha", ""))

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    log = AthleteLog.query.filter_by(user_id=user_id, fecha=fecha).first()

    if not log:
        log = AthleteLog(user_id=user_id, fecha=fecha)
        db.session.add(log)
        db.session.commit()

    rutina, items, tabata_cfg = None, [], None
    if plan and plan.plan_type.lower() == "fuerza":
        rutina = Rutina.query.get(int(plan.main)) if plan.main and plan.main.isdigit() else None
        if rutina:
            tabata_cfg = rutina.tabata_preset
            for it in RutinaItem.query.filter_by(rutina_id=rutina.id).order_by(RutinaItem.posicion).all():
                src = ""
                if it.ejercicio and it.ejercicio.video_filename:
                    src = url_for("static", filename=f"videos/{it.ejercicio.video_filename}")
                items.append({
                    "id": it.id,
                    "nombre": it.nombre,
                    "series": it.series,
                    "reps": it.reps,
                    "descanso": it.descanso,
                    "video_src": src,
                })

    return jsonify({
        "ok": True,
        "plan": {
            "plan_type": plan.plan_type if plan else "Descanso",
            "warmup": plan.warmup if plan else "",
            "main": plan.main if plan else "",
            "finisher": plan.finisher if plan else "",
            "puede_entrenar": plan.puede_entrenar if plan else "si",
            "comentario_atleta": plan.comentario_atleta if plan else "",
        },
        "rutina": {"id": rutina.id, "nombre": rutina.nombre} if rutina else None,
        "items": items,
        "checks": [],
        "log": {
            "did_train": log.did_train,
            "warmup_done": log.warmup_done,
            "main_done": log.main_done,
            "finisher_done": log.finisher_done,
        },
        "is_tabata": bool(tabata_cfg),
        "tabata_cfg": tabata_cfg,
    })
