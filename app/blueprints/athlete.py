# app/blueprints/athlete.py
from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Tuple, Optional

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, DiaPlan, Rutina, RutinaItem, AthleteCheck, AthleteLog

from . import bp
from ._shared import (
    is_admin, safe_parse_ymd, week_dates, month_dates, start_of_week,
    ensure_week_plans, serialize_plan, serialize_rutina,
    _rutina_items_query, build_video_src, normalize_item_video_url,
    compute_streak, week_goal_and_done, get_strength_done_days, get_log_done_days,
    is_tabata_routine
)


@bp.app_context_processor
def _inject_admin():
    return {"is_admin": is_admin, "admin_ok": is_admin()}


@bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id: int):
    user = User.query.get_or_404(user_id)

    if (not is_admin()) and current_user.id != user.id:
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

    view = (request.args.get("view") or "today").strip().lower()
    center = safe_parse_ymd(request.args.get("center", ""), fallback=date.today())
    hoy = date.today()

    plan_hoy = DiaPlan.query.filter_by(user_id=user.id, fecha=hoy).first()
    if not plan_hoy:
        plan_hoy = DiaPlan(user_id=user.id, fecha=hoy, plan_type="Descanso")
        if hasattr(plan_hoy, "puede_entrenar") and getattr(plan_hoy, "puede_entrenar", None) is None:
            plan_hoy.puede_entrenar = "si"
        db.session.add(plan_hoy)
        db.session.commit()

    fechas = week_dates(center)
    planes = ensure_week_plans(user.id, fechas)
    semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"
    done_week = get_strength_done_days(user.id, fechas).union(get_log_done_days(user.id, fechas))

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
            if hasattr(nuevo, "puede_entrenar") and getattr(nuevo, "puede_entrenar", None) is None:
                nuevo.puede_entrenar = "si"
            planes_mes[d] = nuevo
            db.session.add(nuevo)
            changed = True
    if changed:
        db.session.commit()

    done_month = get_strength_done_days(user.id, dias_mes).union(get_log_done_days(user.id, dias_mes))

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
    rutinas = Rutina.query.order_by(Rutina.id.desc()).all()

    done_set: set[Tuple[date, int]] = set()
    checks = AthleteCheck.query.filter(
        AthleteCheck.user_id == user.id,
        AthleteCheck.fecha.in_(fechas)
    ).all()
    for c in checks:
        if c.done:
            done_set.add((c.fecha, c.rutina_item_id))

    logs = AthleteLog.query.filter(
        AthleteLog.user_id == user.id,
        AthleteLog.fecha.in_(fechas)
    ).all()
    log_by_day: Dict[date, AthleteLog] = {l.fecha: l for l in logs}

    streak = compute_streak(user.id)
    week_goal, week_done = week_goal_and_done(user.id, fechas, planes)

    # Strava (si tu app lo usa, lo pasamos; si no existe el modelo/relación, queda None)
    strava_account = None
    try:
        # si tenés integration_accounts o algo, ajustalo acá
        strava_account = getattr(user, "strava_account", None)
    except Exception:
        strava_account = None

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
        strava_account=strava_account,
    )


@bp.route("/api/day_detail")
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
        if hasattr(plan, "puede_entrenar") and getattr(plan, "puede_entrenar", None) is None:
            plan.puede_entrenar = "si"
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
        "tabata_url": "",
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
                items = _rutina_items_query(rid).all()
                payload["rutina"] = serialize_rutina(r)

                if is_tabata_routine(r):
                    payload["tabata_url"] = url_for("main.rutina_tabata_player", rutina_id=r.id)

                out_items = []
                for it in items:
                    out_items.append({
                        "id": it.id,
                        "nombre": it.nombre,
                        "series": getattr(it, "series", "") or "",
                        "reps": getattr(it, "reps", "") or "",
                        "peso": getattr(it, "peso", "") or "",
                        "descanso": getattr(it, "descanso", "") or "",
                        "video_url": normalize_item_video_url(getattr(it, "video_url", "")),
                        "video_src": build_video_src(getattr(it, "video_url", "")),
                        "nota": getattr(it, "nota", "") or "",
                    })
                payload["items"] = out_items

                # ✅ FIX: si no hay items, no hagas .in_() con basura
                item_ids = [it.id for it in items]
                if item_ids:
                    checks = AthleteCheck.query.filter(
                        AthleteCheck.user_id == user_id,
                        AthleteCheck.fecha == fecha,
                        AthleteCheck.rutina_item_id.in_(item_ids),
                    ).all()
                else:
                    checks = []

                done_ids = {c.rutina_item_id for c in checks if c.done}
                payload["checks"] = list(done_ids)

    return jsonify(payload)


@bp.route("/athlete/check_item", methods=["POST"])
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
            if hasattr(existing, "updated_at"):
                existing.updated_at = datetime.utcnow()
        else:
            row = AthleteCheck(
                user_id=user_id,
                fecha=fecha,
                rutina_item_id=item.id,
                done=done
            )
            if hasattr(row, "updated_at"):
                row.updated_at = datetime.utcnow()
            db.session.add(row)

        db.session.commit()
        return jsonify({"ok": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/athlete/save_log", methods=["POST"])
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
        if hasattr(log, "updated_at"):
            log.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({"ok": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/athlete/save_availability", methods=["POST"])
@login_required
def athlete_save_availability():
    try:
        data = request.get_json(silent=True) or {}
        user_id = int(data.get("user_id") or 0)
        fecha = safe_parse_ymd(data.get("fecha", ""), fallback=date.today())
        no_puedo = bool(data.get("no_puedo", False))
        comentario = (data.get("comentario") or "").strip()

        if not user_id:
            return jsonify({"ok": False, "error": "Falta user_id"}), 400
        if (not is_admin()) and current_user.id != user_id:
            return jsonify({"ok": False, "error": "Acceso denegado"}), 403

        plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
        if not plan:
            plan = DiaPlan(user_id=user_id, fecha=fecha, plan_type="Descanso")
            db.session.add(plan)

        if not hasattr(plan, "puede_entrenar") or not hasattr(plan, "comentario_atleta"):
            db.session.rollback()
            return jsonify({
                "ok": False,
                "error": "Faltan columnas en DiaPlan: puede_entrenar / comentario_atleta."
            }), 500

        plan.puede_entrenar = "no" if no_puedo else "si"
        plan.comentario_atleta = comentario

        db.session.commit()
        return jsonify({"ok": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
