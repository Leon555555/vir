# app/routes.py
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from calendar import monthrange
from typing import List, Dict, Any, Optional, Tuple
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
# BLUEPRINTS (se quedan en este archivo, NO carpeta blueprints)
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
        raise ValueError(
            f"Extensión no permitida ({ext}). Permitidas: {', '.join(sorted(ALLOWED_VIDEO_EXT))}"
        )

    folder = videos_dir()
    dest = os.path.join(folder, filename)

    if os.path.exists(dest):
        base, ext2 = os.path.splitext(filename)
        filename = f"{base}_{int(datetime.utcnow().timestamp())}{ext2}"
        dest = os.path.join(folder, filename)

    file_storage.save(dest)
    return filename


def delete_video_from_static(filename: str) -> None:
    safe = secure_filename(filename or "")
    if not safe:
        raise ValueError("Nombre inválido")

    ext = os.path.splitext(safe.lower())[1]
    if ext not in ALLOWED_VIDEO_EXT:
        raise ValueError("Extensión no permitida")

    if safe not in list_repo_videos():
        raise FileNotFoundError("No existe ese archivo en /static/videos")

    path = os.path.join(videos_dir(), safe)
    if not os.path.isfile(path):
        raise FileNotFoundError("Archivo no encontrado")

    os.remove(path)


def _set_if_attr(obj, key: str, value):
    if hasattr(obj, key):
        setattr(obj, key, value)


def parse_rutina_ref(main_field: str) -> Optional[int]:
    s = (main_field or "").strip()
    if not s:
        return None
    s_up = s.upper().replace(" ", "")
    if s_up.startswith("RUTINA:"):
        s_num = s_up.split("RUTINA:", 1)[1]
        try:
            return int(s_num)
        except Exception:
            return None
    try:
        return int(s)
    except Exception:
        return None


# =============================================================
# ✅ NUEVO: PARSER DE BLOQUES EN plan.main (soporta varios TABATA/RUN/FREE)
# =============================================================
def _split_blocks_from_main(main_text: str) -> List[Dict[str, str]]:
    """
    Devuelve lista de bloques base:
      [{"type":"tabata|fuerza|run|free|note", "raw":"...", "label":"..."}]
    Se parsea por líneas (una línea = un bloque).
    """
    lines = [l.strip() for l in (main_text or "").splitlines() if l.strip()]
    out: List[Dict[str, str]] = []
    for line in lines:
        up = line.upper()

        # TABATA
        if up.startswith("TABATA:"):
            payload = line.split(":", 1)[1].strip()
            out.append({"type": "tabata", "raw": payload, "label": "TABATA"})
            continue

        # FUERZA
        if up.startswith("FUERZA:"):
            payload = line.split(":", 1)[1].strip()
            out.append({"type": "fuerza", "raw": payload, "label": "FUERZA"})
            continue

        # RUN
        if up.startswith("RUN:"):
            payload = line.split(":", 1)[1].strip()
            out.append({"type": "run", "raw": payload, "label": "RUN"})
            continue

        # FREE
        if up.startswith("FREE:"):
            payload = line.split(":", 1)[1].strip()
            out.append({"type": "free", "raw": payload, "label": "FREE"})
            continue

        # NOTE
        if up.startswith("NOTE:") or up.startswith("NOTA:"):
            payload = line.split(":", 1)[1].strip()
            out.append({"type": "note", "raw": payload, "label": "NOTA"})
            continue

        # Inferencia:
        rid = parse_rutina_ref(line)
        if rid:
            out.append({"type": "fuerza", "raw": f"RUTINA:{rid}", "label": "FUERZA"})
        else:
            out.append({"type": "free", "raw": line, "label": "FREE"})
    return out


def _rutina_payload(rutina: Rutina) -> Dict[str, Any]:
    return {"id": rutina.id, "nombre": rutina.nombre, "tipo": getattr(rutina, "tipo", "")}


def _items_payload_for_rutina(rutina_id: int) -> List[Dict[str, Any]]:
    ritems = (
        RutinaItem.query
        .filter_by(rutina_id=rutina_id)
        .order_by(RutinaItem.posicion.asc(), RutinaItem.id.asc())
        .all()
    )

    items_payload: List[Dict[str, Any]] = []
    for it in ritems:
        video_src = ""

        if getattr(it, "video_url", None):
            v = (it.video_url or "").strip()
            if v.startswith("http://") or v.startswith("https://"):
                video_src = v
            else:
                v = v.lstrip("/").replace("\\", "/")
                video_src = url_for("static", filename=v)
        elif getattr(it, "ejercicio", None) and getattr(it.ejercicio, "video_filename", None):
            if it.ejercicio.video_filename:
                video_src = url_for("static", filename=f"videos/{it.ejercicio.video_filename}")

        items_payload.append({
            "id": it.id,
            "nombre": it.nombre,
            "series": it.series,
            "reps": it.reps,
            "descanso": it.descanso,
            "nota": getattr(it, "nota", "") or "",
            "video_src": video_src,
        })
    return items_payload


# =============================================================
# DB FIX (TABATA PRESET) - SEGURO
# =============================================================
@main_bp.route("/admin/db_fix_tabata")
@login_required
def admin_db_fix_tabata():
    if not admin_ok():
        return "Acceso denegado", 403

    try:
        db.session.execute(text("""
            ALTER TABLE rutinas
            ADD COLUMN IF NOT EXISTS tabata_preset JSONB;
        """))
        db.session.commit()
        return "OK: columna tabata_preset creada (si faltaba)"
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
    atletas = User.query.filter(User.is_admin.is_(False)).order_by(User.id.desc()).all()
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


# =============================================================
# ✅ NUEVO: ELIMINAR VIDEO DESDE BANCO (ADMIN)
# =============================================================
@main_bp.route("/admin/videos/delete", methods=["POST"])
@login_required
def admin_delete_video():
    if not admin_ok():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    filename = (request.form.get("filename") or "").strip()
    if not filename:
        flash("Falta filename", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    try:
        delete_video_from_static(filename)

        affected = Ejercicio.query.filter(Ejercicio.video_filename == filename).all()
        for e in affected:
            e.video_filename = ""
        db.session.commit()

        flash(f"🗑️ Video eliminado: {filename} (refs DB: {len(affected)})", "success")
    except FileNotFoundError:
        flash("Ese video no existe en /static/videos", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Error eliminando video: {e}", "danger")

    return redirect(url_for("main.dashboard_entrenador"))


# =============================================================
# RUTINA BUILDER
# =============================================================
@main_bp.route("/rutina/<int:rutina_id>/builder", methods=["GET"])
@login_required
def rutina_builder(rutina_id: int):
    if not admin_ok():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    ejercicios = Ejercicio.query.order_by(Ejercicio.nombre.asc()).all()
    items = (
        RutinaItem.query.filter_by(rutina_id=rutina.id)
        .order_by(RutinaItem.posicion.asc(), RutinaItem.id.asc())
        .all()
    )
    return render_template(
        "rutina_builder.html",
        rutina=rutina,
        ejercicios=ejercicios,
        items=items,
    )


@main_bp.route("/rutina/<int:rutina_id>/items/add", methods=["POST"])
@login_required
def rutina_add_item(rutina_id: int):
    if not admin_ok():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)

    ejercicio_id = request.form.get("ejercicio_id", type=int)
    series = (request.form.get("series") or "").strip()
    reps = (request.form.get("reps") or "").strip()
    peso = (request.form.get("peso") or "").strip()
    descanso = (request.form.get("descanso") or "").strip()
    nota = (request.form.get("nota") or "").strip()

    ej = Ejercicio.query.get(ejercicio_id) if ejercicio_id else None
    if not ej:
        flash("Ejercicio inválido", "danger")
        return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))

    max_pos = db.session.query(db.func.max(RutinaItem.posicion)).filter_by(rutina_id=rutina.id).scalar()
    next_pos = int(max_pos or 0) + 1

    it = RutinaItem(
        rutina_id=rutina.id,
        ejercicio_id=ej.id,
        nombre=ej.nombre,
        series=series or None,
        reps=reps or None,
        peso=peso or None,
        descanso=descanso or None,
        nota=nota or None,
        posicion=next_pos,
    )
    db.session.add(it)
    db.session.commit()

    flash("✅ Ejercicio añadido", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))


@main_bp.route("/rutina/<int:rutina_id>/items/<int:item_id>/update", methods=["POST"])
@login_required
def rutina_update_item(rutina_id: int, item_id: int):
    if not admin_ok():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    it = RutinaItem.query.filter_by(id=item_id, rutina_id=rutina.id).first_or_404()

    it.series = (request.form.get("series") or "").strip() or None
    it.reps = (request.form.get("reps") or "").strip() or None
    it.peso = (request.form.get("peso") or "").strip() or None
    it.descanso = (request.form.get("descanso") or "").strip() or None
    it.nota = (request.form.get("nota") or "").strip() or None

    db.session.commit()
    flash("✅ Cambios guardados", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))


@main_bp.route("/rutina/<int:rutina_id>/items/<int:item_id>/delete", methods=["POST"])
@login_required
def rutina_delete_item(rutina_id: int, item_id: int):
    if not admin_ok():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    it = RutinaItem.query.filter_by(id=item_id, rutina_id=rutina.id).first_or_404()

    db.session.delete(it)
    db.session.commit()
    flash("🗑️ Eliminado", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))


@main_bp.route("/rutina/<int:rutina_id>/items/reorder", methods=["POST"])
@login_required
def rutina_reorder(rutina_id: int):
    if not admin_ok():
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403

    data = request.get_json(silent=True) or {}
    order = data.get("order") or []
    if not isinstance(order, list):
        return jsonify({"ok": False, "error": "order inválido"}), 400

    for idx, item_id in enumerate(order):
        try:
            item_id = int(item_id)
        except Exception:
            continue
        it = RutinaItem.query.filter_by(id=item_id, rutina_id=rutina_id).first()
        if it:
            it.posicion = idx

    db.session.commit()
    return jsonify({"ok": True})


# =============================================================
# TABATA SETTINGS + PLAYER (tu lógica actual)
# =============================================================
def _tabata_default_cfg(items_count: int) -> Dict[str, Any]:
    return {
        "title": "Tabata",
        "work": 40,
        "rest": 20,
        "rounds": int(items_count or 10),
        "sets": 1,
        "rest_between_sets": 0,
        "finisher_rest": 60,
        "count_in": 3,
        "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
    }


def _get_tabata_cfg(rutina: Rutina, items_count: int) -> Dict[str, Any]:
    preset = getattr(rutina, "tabata_preset", None)
    base = _tabata_default_cfg(items_count)
    if isinstance(preset, dict):
        base.update(preset)
    return base


def _save_tabata_cfg(rutina: Rutina, cfg: Dict[str, Any]) -> None:
    rutina.tabata_preset = cfg
    db.session.commit()


@main_bp.route("/rutina/<int:rutina_id>/tabata/settings", methods=["GET"])
@login_required
def rutina_tabata_settings(rutina_id: int):
    if not admin_ok():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    items_count = RutinaItem.query.filter_by(rutina_id=rutina.id).count()
    cfg = _get_tabata_cfg(rutina, items_count)

    auto_rounds = items_count

    tabata_work = int(cfg.get("work") or 40)
    tabata_rest = int(cfg.get("rest") or 20)
    tabata_rounds = int(cfg.get("rounds") or 0)
    tabata_sets = int(cfg.get("sets") or 1)
    tabata_rest_between_sets = int(cfg.get("rest_between_sets") or 0)
    tabata_finisher_rest = int(cfg.get("finisher_rest") or 60)
    tabata_count_in = int(cfg.get("count_in") or 3)

    return render_template(
        "rutina_tabata_settings.html",
        rutina=rutina,
        tabata_work=tabata_work,
        tabata_rest=tabata_rest,
        tabata_rounds=tabata_rounds,
        tabata_sets=tabata_sets,
        tabata_rest_between_sets=tabata_rest_between_sets,
        tabata_finisher_rest=tabata_finisher_rest,
        tabata_count_in=tabata_count_in,
        auto_rounds=auto_rounds,
    )


@main_bp.route("/rutina/<int:rutina_id>/tabata/settings/save", methods=["POST"])
@login_required
def rutina_tabata_settings_save(rutina_id: int):
    if not admin_ok():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    items_count = RutinaItem.query.filter_by(rutina_id=rutina.id).count()
    cfg = _get_tabata_cfg(rutina, items_count)

    def _int(name: str, alt: Optional[str] = None, default: int = 0) -> int:
        v = request.form.get(name)
        if (v is None or v == "") and alt:
            v = request.form.get(alt)
        try:
            return int(v) if v is not None and v != "" else int(default)
        except Exception:
            return int(default)

    work = _int("work", "tabata_work", default=int(cfg.get("work") or 40))
    rest = _int("rest", "tabata_rest", default=int(cfg.get("rest") or 20))
    rounds = _int("rounds", "tabata_rounds", default=int(cfg.get("rounds") or items_count or 10))
    recovery = _int("recovery", "tabata_finisher_rest", default=int(cfg.get("finisher_rest") or 60))

    sets_ = _int("tabata_sets", None, default=int(cfg.get("sets") or 1))
    rest_between_sets = _int("tabata_rest_between_sets", None, default=int(cfg.get("rest_between_sets") or 0))
    count_in = _int("tabata_count_in", None, default=int(cfg.get("count_in") or 3))

    if rounds <= 0:
        rounds = int(items_count or 10)

    cfg.update({
        "work": max(5, work),
        "rest": max(0, rest),
        "rounds": max(1, rounds),
        "sets": max(1, sets_),
        "rest_between_sets": max(0, rest_between_sets),
        "finisher_rest": max(0, recovery),
        "count_in": max(0, min(30, count_in)),
        "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
    })

    try:
        _save_tabata_cfg(rutina, cfg)
        flash("✅ Preset TABATA guardado", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error guardando Tabata: {e}", "danger")

    return redirect(url_for("main.rutina_tabata_player", rutina_id=rutina.id))


@main_bp.route("/rutina/<int:rutina_id>/tabata", methods=["GET", "POST"])
@login_required
def rutina_tabata_player(rutina_id: int):
    if not (admin_ok() or current_user.is_authenticated):
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)

    ritems = (
        RutinaItem.query
        .filter_by(rutina_id=rutina.id)
        .order_by(RutinaItem.posicion.asc(), RutinaItem.id.asc())
        .all()
    )

    cfg = _get_tabata_cfg(rutina, len(ritems))

    if request.method == "POST":
        if not admin_ok():
            flash("Solo admin puede guardar", "danger")
            return redirect(url_for("main.rutina_tabata_player", rutina_id=rutina.id))

        title = (request.form.get("title") or cfg.get("title") or "Tabata").strip()
        work = int(request.form.get("work") or cfg.get("work") or 40)
        rest = int(request.form.get("rest") or cfg.get("rest") or 20)
        rounds = int(request.form.get("rounds") or cfg.get("rounds") or (len(ritems) or 10))
        recovery = int(request.form.get("recovery") or cfg.get("finisher_rest") or 60)

        if rounds <= 0:
            rounds = len(ritems) or 10

        cfg.update({
            "title": title or "Tabata",
            "work": max(5, work),
            "rest": max(0, rest),
            "rounds": max(1, rounds),
            "finisher_rest": max(0, recovery),
            "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
        })

        try:
            _save_tabata_cfg(rutina, cfg)
            flash("✅ Config Tabata guardada", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error guardando Tabata: {e}", "danger")

        return redirect(url_for("main.rutina_tabata_player", rutina_id=rutina.id))

    items_payload: List[Dict[str, Any]] = []
    for it in ritems:
        video_src = ""

        if getattr(it, "video_url", None):
            v = (it.video_url or "").strip()
            if v.startswith("http://") or v.startswith("https://"):
                video_src = v
            else:
                v = v.lstrip("/").replace("\\", "/")
                video_src = url_for("static", filename=v)
        elif getattr(it, "ejercicio", None) and getattr(it.ejercicio, "video_filename", None):
            if it.ejercicio.video_filename:
                video_src = url_for("static", filename=f"videos/{it.ejercicio.video_filename}")

        items_payload.append({
            "id": it.id,
            "nombre": it.nombre,
            "nota": getattr(it, "nota", "") or "",
            "video_src": video_src,
        })

    cfg_for_template = dict(cfg)
    cfg_for_template["recovery"] = int(cfg.get("finisher_rest") or 60)

    return render_template(
        "tabata_player.html",
        rutina=rutina,
        cfg=cfg_for_template,
        items_payload=items_payload,
        is_admin=admin_ok(),
    )


# =============================================================
# PLANIFICADOR
# =============================================================
@main_bp.route("/coach/planificador")
@login_required
def coach_planificador():
    if not admin_ok():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    atletas = User.query.filter(User.is_admin.is_(False)).order_by(User.id.desc()).all()
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

    plan.warmup = (request.form.get("warmup") or "").strip()
    plan.finisher = (request.form.get("finisher") or "").strip()

    # 🔥 No tocamos tu lógica: si es Fuerza, guardamos rutina_select; si no, main libre.
    if plan_type.lower() == "fuerza":
        rutina_select = (request.form.get("rutina_select") or "").strip()
        plan.main = rutina_select
    else:
        plan.main = (request.form.get("main") or "").strip()

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
            flash("⚠️ Video subido al server (en Render puede perderse). Ideal: seleccionar existente.", "warning")
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
    if user.is_admin:
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
# ✅ API: DAY DETAIL (MODAL) — AHORA DEVUELVE "blocks" (varios Tabatas)
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

    # ---- blocks desde plan.main (y fallback a comportamiento anterior)
    blocks_src = _split_blocks_from_main(plan.main or "")

    # Fallback: si main está vacío pero es fuerza, intentamos parsear rutina directa
    if not blocks_src and (plan.plan_type or "").lower() == "fuerza" and (plan.main or "").strip():
        blocks_src = [{"type": "fuerza", "raw": plan.main.strip(), "label": "FUERZA"}]

    blocks: List[Dict[str, Any]] = []
    legacy_items_payload: List[Dict[str, Any]] = []
    legacy_is_tabata = False
    legacy_tabata_cfg = None
    legacy_rutina = None

    for b in blocks_src:
        btype = b["type"]
        raw = (b["raw"] or "").strip()

        # TABATA: apunta a Rutina
        if btype == "tabata":
            rid = parse_rutina_ref(raw.replace("RUTINA:", "RUTINA:"))
            # también soporta "RUTINA:12" directo
            if not rid and raw.upper().startswith("RUTINA:"):
                rid = parse_rutina_ref(raw)
            if not rid:
                # si pusieron TABATA:12
                rid = parse_rutina_ref(raw)

            rutina = Rutina.query.get(rid) if rid else None
            if not rutina:
                blocks.append({
                    "type": "tabata",
                    "ok": False,
                    "title": "Tabata",
                    "error": "Rutina no encontrada",
                })
                continue

            items = _items_payload_for_rutina(rutina.id)
            cfg = _get_tabata_cfg(rutina, len(items))

            blocks.append({
                "type": "tabata",
                "ok": True,
                "rutina": _rutina_payload(rutina),
                "cfg": cfg,
                "items": items,
                "start_url": url_for("main.rutina_tabata_player", rutina_id=rutina.id),
                "settings_url": url_for("main.rutina_tabata_settings", rutina_id=rutina.id) if admin_ok() else "",
            })

            # legacy (primer tabata para compatibilidad vieja)
            if legacy_rutina is None:
                legacy_rutina = rutina
                legacy_is_tabata = True
                legacy_tabata_cfg = cfg
                legacy_items_payload = items

            continue

        # FUERZA: rutina lista de ejercicios (no tabata)
        if btype == "fuerza":
            rid = parse_rutina_ref(raw)
            rutina = Rutina.query.get(rid) if rid else None
            if not rutina:
                blocks.append({
                    "type": "fuerza",
                    "ok": False,
                    "title": "Fuerza",
                    "error": "Rutina no encontrada",
                })
                continue

            items = _items_payload_for_rutina(rutina.id)
            blocks.append({
                "type": "fuerza",
                "ok": True,
                "rutina": _rutina_payload(rutina),
                "items": items,
                "builder_url": url_for("main.rutina_builder", rutina_id=rutina.id) if admin_ok() else "",
            })

            if legacy_rutina is None:
                legacy_rutina = rutina
                legacy_items_payload = items

            continue

        # RUN/FREE/NOTE: texto bonito
        if btype in ("run", "free", "note"):
            blocks.append({
                "type": btype,
                "ok": True,
                "text": raw,
            })
            continue

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
        # NUEVO
        "blocks": blocks,
        # LEGACY (por si algo viejo lo usaba)
        "rutina": ({"id": legacy_rutina.id, "nombre": legacy_rutina.nombre} if legacy_rutina else None),
        "items": legacy_items_payload,
        "checks": done_ids,
        "log": {
            "did_train": bool(log.did_train),
            "warmup_done": log.warmup_done,
            "main_done": log.main_done,
            "finisher_done": log.finisher_done,
        },
        "is_tabata": bool(legacy_is_tabata),
        "tabata_cfg": legacy_tabata_cfg,
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
