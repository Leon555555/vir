# app/routes/__init__.py
from __future__ import annotations

from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import Any, Dict, List, Tuple, Optional

import os
import time
import json

from werkzeug.utils import secure_filename
from flask import Blueprint, current_app, url_for
from flask_login import current_user

from sqlalchemy import func

from app.extensions import db
from app.models import (
    User, DiaPlan, Rutina, Ejercicio, RutinaItem,
    AthleteCheck, AthleteLog
)

# ✅ Un SOLO blueprint para mantener url_for('main.xxx')
main_bp = Blueprint("main", __name__)

# =============================================================
# MEDIA / VIDEOS (FREE SAFE MODE)
# =============================================================
ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v"}


def videos_dir() -> str:
    """
    Carpeta canonical de videos estáticos:
    app/static/videos
    """
    folder = os.path.join(current_app.static_folder, "videos")
    os.makedirs(folder, exist_ok=True)
    return folder


def list_repo_videos() -> List[str]:
    """
    Lista archivos disponibles en app/static/videos (repo).
    """
    folder = videos_dir()
    out: List[str] = []
    try:
        for fn in os.listdir(folder):
            p = os.path.join(folder, fn)
            if not os.path.isfile(p):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in ALLOWED_VIDEO_EXT:
                out.append(fn)
    except Exception:
        return []
    out.sort(key=lambda s: s.lower())
    return out


def save_video_to_static(file_storage) -> str:
    """
    OJO: en Render gratis NO es persistente (se pierde).
    Local OK.
    """
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValueError("Nombre de archivo no válido")

    name, ext = os.path.splitext(filename)
    ext = (ext or "").lower()
    if ext not in ALLOWED_VIDEO_EXT:
        raise ValueError(f"Formato no permitido ({ext}). Usá: {', '.join(sorted(ALLOWED_VIDEO_EXT))}")

    safe = f"{name.strip()}_{int(time.time())}{ext}"
    out_path = os.path.join(videos_dir(), safe)
    file_storage.save(out_path)
    return safe


def normalize_item_video_url(v: str | None) -> str:
    """
    Guardamos/mostramos siempre como 'videos/<filename>' (sin /static).
    """
    if not v:
        return ""
    s = str(v).strip()
    if not s:
        return ""
    if s.startswith("/static/"):
        s = s.replace("/static/", "", 1)
    if s.startswith("static/"):
        s = s.replace("static/", "", 1)
    if "/" not in s:
        s = f"videos/{s}"
    return s


def build_video_src(video_url: str | None) -> str:
    """
    Devuelve url absoluta a /static/videos/...
    """
    rel = normalize_item_video_url(video_url)
    if not rel:
        return ""
    return url_for("static", filename=rel)


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
    if not s:
        return fallback or date.today()
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
        "fecha": p.fecha.strftime("%Y-%m-%d") if hasattr(p.fecha, "strftime") else str(p.fecha),
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
            if hasattr(nuevo, "puede_entrenar") and getattr(nuevo, "puede_entrenar", None) is None:
                nuevo.puede_entrenar = "si"
            planes[f] = nuevo
            db.session.add(nuevo)
            changed = True

    if changed:
        db.session.commit()

    return planes


def _rutina_items_query(rid: int):
    """
    Orden seguro:
    - si existe RutinaItem.posicion -> order_by(posicion, id)
    - si no -> order_by(id)
    """
    q = RutinaItem.query.filter_by(rutina_id=rid)
    if hasattr(RutinaItem, "posicion"):
        return q.order_by(RutinaItem.posicion.asc(), RutinaItem.id.asc())
    return q.order_by(RutinaItem.id.asc())


def get_strength_done_days(user_id: int, fechas: List[date]) -> set[date]:
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

        items = _rutina_items_query(rid).all()
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
    today = date.today()
    streak = 0

    for i in range(0, 365):
        d = today - timedelta(days=i)

        log = AthleteLog.query.filter_by(user_id=user_id, fecha=d).first()
        if log and log.did_train:
            streak += 1
            continue

        plan = DiaPlan.query.filter_by(user_id=user_id, fecha=d).first()
        if plan and (plan.plan_type or "").lower() == "fuerza" and plan.main and isinstance(plan.main, str) and plan.main.startswith("RUTINA:"):
            rid_str = plan.main.split(":", 1)[1].strip()
            if rid_str.isdigit():
                rid = int(rid_str)
                items = _rutina_items_query(rid).all()
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
        break

    return streak


def week_goal_and_done(user_id: int, fechas: List[date], planes: Dict[date, DiaPlan]) -> Tuple[int, int]:
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
# Importar módulos para “registrar” rutas en main_bp
# =============================================================
from . import auth  # noqa: E402,F401
from . import coach  # noqa: E402,F401
from . import athlete  # noqa: E402,F401
from . import routines  # noqa: E402,F401
from . import tabata  # noqa: E402,F401
from . import media  # noqa: E402,F401
from . import ai  # noqa: E402,F401
