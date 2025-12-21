# app/blueprints/tabata.py
from __future__ import annotations

import json
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from app.models import Rutina
from . import bp
from ._shared import (
    is_admin,
    _rutina_items_query,
    build_video_src,
    normalize_item_video_url,
    is_tabata_routine,
)

def _int_arg(name: str, default: int) -> int:
    try:
        v = int(request.args.get(name, default))
        return max(0, v)
    except Exception:
        return default

def _int_form(name: str, default: int) -> int:
    try:
        v = int(request.form.get(name, default))
        return max(0, v)
    except Exception:
        return default


@bp.route("/rutinas/<int:rutina_id>/tabata")
@login_required
def rutina_tabata_player(rutina_id: int):
    rutina = Rutina.query.get_or_404(rutina_id)

    # Tabata lo puede ver el atleta (no solo admin)
    # Si querés restringir:
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

    cfg = {
        "work": _int_arg("work", 40),
        "rest": _int_arg("rest", 20),
        "rounds": _int_arg("rounds", max(1, len(player_items))),
        "sets": _int_arg("sets", 1),
        "rest_between_sets": _int_arg("rest_between_sets", 60),
        "finisher_rest": _int_arg("finisher_rest", 60),
        "count_in": _int_arg("count_in", 5),
    }

    # Ajustes
    if player_items and cfg["rounds"] > len(player_items):
        cfg["rounds"] = len(player_items)

    cfg["work"] = max(5, cfg["work"])
    cfg["rest"] = max(0, cfg["rest"])
    cfg["rounds"] = max(1, cfg["rounds"])
    cfg["sets"] = max(1, cfg["sets"])
    cfg["rest_between_sets"] = max(0, cfg["rest_between_sets"])
    cfg["finisher_rest"] = max(0, cfg["finisher_rest"])
    cfg["count_in"] = max(0, cfg["count_in"])

    return render_template(
        "rutina_tabata.html",
        rutina=rutina,
        tabata_cfg=cfg,
        tabata_items=player_items,
        tabata_items_json=json.dumps(player_items, ensure_ascii=False),
        tabata_cfg_json=json.dumps(cfg, ensure_ascii=False),
    )


# ==========================================================
# ✅ TABATA SETTINGS (para evitar el BuildError del builder)
# ==========================================================

@bp.route("/rutinas/<int:rutina_id>/tabata/settings", methods=["GET"])
@login_required
def rutina_tabata_settings(rutina_id: int):
    """
    Pantalla opcional de settings (admin). No es obligatoria para que funcione el builder.
    """
    if not is_admin():
        flash("Solo admin", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    items = _rutina_items_query(rutina.id).all()
    auto_rounds = max(1, len(items))

    work = _int_arg("work", 40)
    rest = _int_arg("rest", 20)
    rounds = _int_arg("rounds", auto_rounds)
    recovery = _int_arg("recovery", 60)

    if rounds <= 0:
        rounds = auto_rounds
    if items and rounds > len(items):
        rounds = len(items)

    return render_template(
        "rutina_tabata_settings.html",
        rutina=rutina,
        tabata_work=work,
        tabata_rest=rest,
        tabata_rounds=rounds,
        tabata_recovery=recovery,
        auto_rounds=auto_rounds,
    )


@bp.route("/rutinas/<int:rutina_id>/tabata/settings/save", methods=["POST"])
@login_required
def rutina_tabata_settings_save(rutina_id: int):
    """
    ✅ Endpoint que tu rutina_builder.html necesita:
    url_for('main.rutina_tabata_settings_save', rutina_id=...)

    Lee EXACTO los campos del builder:
      - work, rest, rounds, recovery

    No persiste DB (sin migraciones): redirige al player con querystring.
    """
    if not is_admin():
        flash("Solo admin", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)

    # nombres exactos del form del builder
    work = _int_form("work", 40)
    rest = _int_form("rest", 20)
    rounds = _int_form("rounds", 0)
    recovery = _int_form("recovery", 60)

    items = _rutina_items_query(rutina.id).all()
    if rounds <= 0:
        rounds = max(1, len(items))
    if items and rounds > len(items):
        rounds = len(items)

    work = max(5, work)
    rest = max(0, rest)
    rounds = max(1, rounds)
    recovery = max(0, recovery)

    flash("✅ Preset TABATA guardado", "success")

    return redirect(url_for(
        "main.rutina_tabata_player",
        rutina_id=rutina.id,
        work=work,
        rest=rest,
        rounds=rounds,
        finisher_rest=recovery,  # mapeo recovery -> finisher_rest
    ))
