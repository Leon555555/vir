# app/blueprints/tabata.py
from __future__ import annotations

import json
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from app.models import Rutina
from . import bp
from ._shared import is_admin, _rutina_items_query, build_video_src, normalize_item_video_url, is_tabata_routine

def _int_arg(name: str, default: int) -> int:
    try:
        v = int(request.args.get(name, default))
        return max(0, v)
    except Exception:
        return default

@bp.route("/rutinas/<int:rutina_id>/tabata")
@login_required
def rutina_tabata_player(rutina_id: int):
    rutina = Rutina.query.get_or_404(rutina_id)

    # Tabata lo puede ver el atleta (no solo admin)
    # pero si querés restringirlo: descomentá:
    # if not is_admin():
    #     flash("Acceso denegado", "danger")
    #     return redirect(url_for("main.perfil_redirect"))

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

    # Config por defecto (tu ejemplo)
    cfg = {
        "work": _int_arg("work", 40),                 # segundos
        "rest": _int_arg("rest", 20),                 # segundos
        "rounds": _int_arg("rounds", max(1, len(player_items))),  # cuántos ejercicios por vuelta
        "sets": _int_arg("sets", 1),                  # cuántas vueltas
        "rest_between_sets": _int_arg("rest_between_sets", 60),   # descanso entre vueltas
        "finisher_rest": _int_arg("finisher_rest", 60),           # descanso final
        "count_in": _int_arg("count_in", 5),          # cuenta atrás inicial
    }

    # Si la rutina tiene menos ejercicios que rounds, ajustamos
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
