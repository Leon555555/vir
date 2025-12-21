# app/blueprints/tabata.py
from __future__ import annotations

import json
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required

from app.models import Rutina
from . import bp
from ._shared import (
    is_admin,
    _rutina_items_query,
    build_video_src,
    normalize_item_video_url,
)

def _int(v, default: int) -> int:
    try:
        return max(0, int(v))
    except Exception:
        return default

def _int_arg(name: str, default: int) -> int:
    return _int(request.args.get(name, default), default)

def _session_key(rutina_id: int) -> str:
    return f"tabata_preset:{rutina_id}"

@bp.route("/rutinas/<int:rutina_id>/tabata")
@login_required
def rutina_tabata_player(rutina_id: int):
    rutina = Rutina.query.get_or_404(rutina_id)
    items = _rutina_items_query(rutina.id).all()

    player_items = []
    for it in items:
        player_items.append({
            "id": it.id,
            "nombre": it.nombre,
            "video_src": build_video_src(getattr(it, "video_url", "")),
            "video_url": normalize_item_video_url(getattr(it, "video_url", "")),
            "series": getattr(it, "series", "") or "",
            "reps": getattr(it, "reps", "") or "",
            "peso": getattr(it, "peso", "") or "",
            "descanso": getattr(it, "descanso", "") or "",
            "nota": getattr(it, "nota", "") or "",
        })

    preset = session.get(_session_key(rutina_id)) or {}

    cfg = {
        "work": _int_arg("work", _int(preset.get("work", 40), 40)),
        "rest": _int_arg("rest", _int(preset.get("rest", 20), 20)),
        "rounds": _int_arg("rounds", _int(preset.get("rounds", max(1, len(player_items))), max(1, len(player_items)))),
        "sets": _int_arg("sets", _int(preset.get("sets", 1), 1)),
        "rest_between_sets": _int_arg("rest_between_sets", _int(preset.get("rest_between_sets", 60), 60)),
        "finisher_rest": _int_arg("finisher_rest", _int(preset.get("finisher_rest", 60), 60)),
        "count_in": _int_arg("count_in", _int(preset.get("count_in", 5), 5)),
    }

    if player_items and cfg["rounds"] > len(player_items):
        cfg["rounds"] = len(player_items)

    return render_template(
        "rutina_tabata.html",
        rutina=rutina,
        tabata_cfg=cfg,
        tabata_items=player_items,
        tabata_items_json=json.dumps(player_items, ensure_ascii=False),
        tabata_cfg_json=json.dumps(cfg, ensure_ascii=False),
    )

# ✅ ENDPOINT QUE TU rutina_builder.html PIDE
@bp.route("/rutinas/<int:rutina_id>/tabata/settings/save", methods=["POST"])
@login_required
def rutina_tabata_settings_save(rutina_id: int):
    if not is_admin():
        flash("Solo admin puede guardar preset TABATA", "danger")
        return redirect(url_for("main.perfil_redirect"))

    work = _int(request.form.get("work"), 40)
    rest = _int(request.form.get("rest"), 20)
    rounds = _int(request.form.get("rounds"), 10)
    finisher_rest = _int(request.form.get("recovery"), 60)

    preset = {
        "work": work,
        "rest": rest,
        "rounds": rounds,
        "sets": 1,
        "rest_between_sets": 60,
        "finisher_rest": finisher_rest,
        "count_in": 5,
    }

    session[_session_key(rutina_id)] = preset
    session.modified = True

    flash("✅ Preset TABATA guardado", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))
