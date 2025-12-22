# app/blueprints/athlete.py
from __future__ import annotations

import json
from datetime import date, datetime

from flask import request, jsonify, url_for, render_template, redirect, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, DiaPlan, AthleteLog, AthleteCheck, Rutina
from . import bp
from ._shared import (
    safe_parse_ymd,
    ensure_week_plans,
    week_dates,
    month_dates,
    serialize_plan,
    _rutina_items_query,
    build_video_src,
    normalize_item_video_url,
    is_tabata_routine,
    compute_streak,
    week_goal_and_done,
    get_strength_done_days,
    get_log_done_days,
)


def _get_or_create_log(user_id: int, d: date) -> AthleteLog:
    log = AthleteLog.query.filter_by(user_id=user_id, fecha=d).first()
    if not log:
        log = AthleteLog(user_id=user_id, fecha=d, did_train=False)
        db.session.add(log)
        db.session.commit()
    return log


@bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id: int):
    # atleta ve su perfil, admin puede ver cualquiera
    if current_user.id != user_id and not getattr(current_user, "is_admin", False):
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    user = User.query.get_or_404(user_id)

    view = request.args.get("view", "today")
    center = safe_parse_ymd(request.args.get("center", ""), fallback=date.today())

    hoy = date.today()

    # streak + semana
    fechas_sem = week_dates(center)
    planes_sem = ensure_week_plans(user.id, fechas_sem)
    week_goal, week_done = week_goal_and_done(user.id, fechas_sem, planes_sem)
    streak = compute_streak(user.id)

    done_week = get_strength_done_days(user.id, fechas_sem).union(get_log_done_days(user.id, fechas_sem))

    # plan hoy
    plan_hoy = planes_sem.get(hoy)
    if not plan_hoy:
        plan_hoy = DiaPlan(user_id=user.id, fecha=hoy, plan_type="Descanso")
        db.session.add(plan_hoy)
        db.session.commit()

    # month view
    y = center.year
    m = center.month
    days = month_dates(y, m)

    # grid (7 cols)
    import calendar
    cal = calendar.Calendar(firstweekday=0)  # lunes
    month_grid = []
    week = []
    for d in cal.itermonthdates(y, m):
        if d.month != m:
            week.append(None)
        else:
            week.append(d)
        if len(week) == 7:
            month_grid.append(week)
            week = []
    if week:
        while len(week) < 7:
            week.append(None)
        month_grid.append(week)

    planes_mes_db = DiaPlan.query.filter(DiaPlan.user_id == user.id, DiaPlan.fecha.in_(days)).all()
    planes_mes = {p.fecha: p for p in planes_mes_db}
    # asegurar existan
    changed = False
    for d in days:
        if d not in planes_mes:
            p = DiaPlan(user_id=user.id, fecha=d, plan_type="Descanso", puede_entrenar="si")
            db.session.add(p)
            planes_mes[d] = p
            changed = True
    if changed:
        db.session.commit()

    semana_str = f"{fechas_sem[0].strftime('%d/%m')} – {fechas_sem[-1].strftime('%d/%m')}"
    month_label = center.strftime("%B %Y").capitalize()

    # strava account (si existe)
    strava_account = getattr(user, "strava_account", None)

    return render_template(
        "perfil.html",
        user=user,
        view=view,
        center=center,
        hoy=hoy,
        plan_hoy=plan_hoy,
        fechas=fechas_sem,
        planes=planes_sem,
        done_week=done_week,
        semana_str=semana_str,
        month_label=month_label,
        month_grid=month_grid,
        planes_mes=planes_mes,
        week_goal=week_goal,
        week_done=week_done,
        streak=streak,
        strava_account=strava_account,
    )


@bp.route("/api/day_detail")
@login_required
def api_day_detail():
    user_id = int(request.args.get("user_id", current_user.id))
    fecha = safe_parse_ymd(request.args.get("fecha", ""), fallback=date.today())

    if current_user.id != user_id and not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha, plan_type="Descanso", puede_entrenar="si")
        db.session.add(plan)
        db.session.commit()

    log = AthleteLog.query.filter_by(user_id=user_id, fecha=fecha).first()

    payload = {
        "ok": True,
        "fecha": fecha.isoformat(),
        "plan": serialize_plan(plan),
        "rutina": None,
        "items": [],
        "checks": [],
        "log": None,
        "tabata_url": "",
        "is_tabata": False,
        "tabata_cfg": None,
    }

    # log
    if log:
        payload["log"] = {
            "did_train": bool(log.did_train),
            "warmup_done": log.warmup_done or "",
            "main_done": log.main_done or "",
            "finisher_done": log.finisher_done or "",
        }

    # fuerza: si main empieza con RUTINA:ID
    rid = None
    main = (plan.main or "")
    if isinstance(main, str) and main.startswith("RUTINA:"):
        rid_str = main.split(":", 1)[1].strip()
        if rid_str.isdigit():
            rid = int(rid_str)

    if rid:
        r = Rutina.query.get(rid)
        if r:
            payload["rutina"] = {"id": r.id, "nombre": r.nombre, "tipo": r.tipo or ""}

            items = _rutina_items_query(r.id).all()
            out_items = []
            for it in items:
                out_items.append({
                    "id": it.id,
                    "nombre": it.nombre,
                    "series": it.series or "",
                    "reps": it.reps or "",
                    "peso": it.peso or "",
                    "descanso": it.descanso or "",
                    "nota": it.nota or "",
                    "video_src": build_video_src(getattr(it, "video_url", "")),
                    "video_url": normalize_item_video_url(getattr(it, "video_url", "")),
                })
            payload["items"] = out_items

            checks = AthleteCheck.query.filter(
                AthleteCheck.user_id == user_id,
                AthleteCheck.fecha == fecha,
                AthleteCheck.rutina_item_id.in_([it.id for it in items]) if items else [0]
            ).all()
            payload["checks"] = [c.rutina_item_id for c in checks if c.done]

            # ✅ TABATA cfg desde DB
            if is_tabata_routine(r):
                payload["tabata_url"] = url_for("main.rutina_tabata_player", rutina_id=r.id)
                payload["is_tabata"] = True
                cfg = None
                try:
                    raw = (getattr(r, "tabata_preset", None) or "").strip()
                    cfg = json.loads(raw) if raw else None
                except Exception:
                    cfg = None

                if not cfg:
                    cfg = {
                        "work": 40, "rest": 20,
                        "rounds": max(1, len(out_items)),
                        "sets": 1,
                        "rest_between_sets": 60,
                        "finisher_rest": 60,
                        "count_in": 3
                    }
                payload["tabata_cfg"] = cfg

    return jsonify(payload)


@bp.route("/athlete/check_item", methods=["POST"])
@login_required
def athlete_check_item():
    user_id = int(request.form.get("user_id", current_user.id))
    fecha = safe_parse_ymd(request.form.get("fecha", ""), fallback=date.today())
    item_id = int(request.form.get("item_id", 0))
    done = request.form.get("done", "0") in ("1", "true", "True", "on")

    if current_user.id != user_id and not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403
    if item_id <= 0:
        return jsonify({"ok": False, "error": "item_id inválido"}), 400

    chk = AthleteCheck.query.filter_by(user_id=user_id, fecha=fecha, rutina_item_id=item_id).first()
    if not chk:
        chk = AthleteCheck(user_id=user_id, fecha=fecha, rutina_item_id=item_id, done=done)
        db.session.add(chk)
    else:
        chk.done = done
        chk.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/athlete/save_log", methods=["POST"])
@login_required
def athlete_save_log():
    data = request.get_json(force=True, silent=True) or {}
    user_id = int(data.get("user_id", current_user.id))
    fecha = safe_parse_ymd(str(data.get("fecha", "")), fallback=date.today())

    if current_user.id != user_id and not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403

    log = AthleteLog.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not log:
        log = AthleteLog(user_id=user_id, fecha=fecha)
        db.session.add(log)

    log.did_train = bool(data.get("did_train", False))
    log.warmup_done = (data.get("warmup_done") or "")
    log.main_done = (data.get("main_done") or "")
    log.finisher_done = (data.get("finisher_done") or "")
    log.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/athlete/save_availability", methods=["POST"])
@login_required
def athlete_save_availability():
    data = request.get_json(force=True, silent=True) or {}
    user_id = int(data.get("user_id", current_user.id))
    fecha = safe_parse_ymd(str(data.get("fecha", "")), fallback=date.today())
    no_puedo = bool(data.get("no_puedo", False))
    comentario = (data.get("comentario") or "").strip()

    if current_user.id != user_id and not getattr(current_user, "is_admin", False):
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha, plan_type="Descanso", puede_entrenar="si")
        db.session.add(plan)

    plan.puede_entrenar = "no" if no_puedo else "si"
    plan.comentario_atleta = comentario
    db.session.commit()

    return jsonify({"ok": True})
