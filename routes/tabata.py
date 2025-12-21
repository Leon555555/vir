# app/routes/tabata.py
from __future__ import annotations

from flask import render_template, request, abort
from flask_login import login_required, current_user

from app.models import Rutina, RutinaItem
from . import main_bp, is_admin, build_video_src


@main_bp.route("/rutinas/<int:rutina_id>/tabata")
@login_required
def rutina_tabata_player(rutina_id: int):
    """
    Player TABATA:
    /rutinas/<id>/tabata?work=40&rest=20&rounds=10&final=60
    """
    rutina = Rutina.query.get_or_404(rutina_id)

    # Seguridad: el atleta puede ver si la rutina le corresponde vía plan.
    # (lo dejamos abierto por ahora porque ya lo llamás desde api_day_detail)
    items_q = RutinaItem.query.filter_by(rutina_id=rutina.id)
    if hasattr(RutinaItem, "posicion"):
        items_q = items_q.order_by(RutinaItem.posicion.asc(), RutinaItem.id.asc())
    else:
        items_q = items_q.order_by(RutinaItem.id.asc())

    items = items_q.all()
    if not items:
        abort(404, "Rutina sin ejercicios")

    # Config editable (opción B)
    work = int(request.args.get("work", 40))
    rest = int(request.args.get("rest", 20))
    rounds = int(request.args.get("rounds", len(items)))
    final_rest = int(request.args.get("final", 60))

    # limit básico
    work = max(5, min(work, 300))
    rest = max(0, min(rest, 300))
    rounds = max(1, min(rounds, 50))
    final_rest = max(0, min(final_rest, 600))

    # armamos items para el player
    player_items = []
    for it in items[:rounds]:
        player_items.append({
            "id": it.id,
            "name": it.nombre,
            "video": build_video_src(getattr(it, "video_url", "")),
        })

    return render_template(
        "rutina_tabata.html",
        rutina=rutina,
        work=work,
        rest=rest,
        rounds=rounds,
        final_rest=final_rest,
        items=player_items,
    )
