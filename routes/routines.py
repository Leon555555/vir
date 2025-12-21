# app/routes/routines.py
from __future__ import annotations

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required

from sqlalchemy import func

from app.extensions import db
from app.models import Rutina, Ejercicio, RutinaItem

from . import main_bp, is_admin


def _items_query(rid: int):
    q = RutinaItem.query.filter_by(rutina_id=rid)
    if hasattr(RutinaItem, "posicion"):
        return q.order_by(RutinaItem.posicion.asc(), RutinaItem.id.asc())
    return q.order_by(RutinaItem.id.asc())


@main_bp.route("/rutinas/<int:rutina_id>/builder")
@login_required
def rutina_builder(rutina_id: int):
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    items = _items_query(rutina.id).all()
    ejercicios = Ejercicio.query.order_by(Ejercicio.nombre).all()
    return render_template("rutina_builder.html", rutina=rutina, items=items, ejercicios=ejercicios)


@main_bp.route("/rutinas/<int:rutina_id>/add_item", methods=["POST"])
@login_required
def rutina_add_item(rutina_id: int):
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    ejercicio_id = request.form.get("ejercicio_id", type=int)
    if not ejercicio_id:
        flash("Falta el ejercicio a añadir", "danger")
        return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))

    ejercicio = Ejercicio.query.get_or_404(ejercicio_id)

    vurl = f"videos/{ejercicio.video_filename}" if getattr(ejercicio, "video_filename", None) else ""

    next_pos = None
    if hasattr(RutinaItem, "posicion"):
        max_pos = db.session.query(func.max(RutinaItem.posicion)).filter_by(rutina_id=rutina.id).scalar()
        next_pos = int(max_pos) + 1 if max_pos is not None else 0

    item = RutinaItem(
        rutina_id=rutina.id,
        ejercicio_id=ejercicio.id,
        nombre=ejercicio.nombre,
        series=(request.form.get("series") or "").strip(),
        reps=(request.form.get("reps") or "").strip(),
        descanso=(request.form.get("descanso") or "").strip(),
        nota=(request.form.get("nota") or "").strip(),
        video_url=vurl
    )

    if hasattr(item, "peso"):
        item.peso = (request.form.get("peso") or "").strip()
    if hasattr(item, "posicion") and next_pos is not None:
        item.posicion = next_pos

    db.session.add(item)
    db.session.commit()

    flash("✅ Ejercicio añadido", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))


@main_bp.route("/rutinas/<int:rutina_id>/items/<int:item_id>/update", methods=["POST"])
@login_required
def rutina_update_item(rutina_id: int, item_id: int):
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    item = RutinaItem.query.get_or_404(item_id)
    if item.rutina_id != rutina_id:
        flash("Item no corresponde a la rutina", "danger")
        return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))

    item.series = (request.form.get("series") or "").strip()
    item.reps = (request.form.get("reps") or "").strip()
    item.descanso = (request.form.get("descanso") or "").strip()
    item.nota = (request.form.get("nota") or "").strip()

    if hasattr(item, "peso"):
        item.peso = (request.form.get("peso") or "").strip()

    db.session.commit()
    flash("✅ Cambios guardados", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))


@main_bp.route("/rutinas/<int:rutina_id>/items/<int:item_id>/delete", methods=["POST"])
@login_required
def rutina_delete_item(rutina_id: int, item_id: int):
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    item = RutinaItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()

    flash("🗑️ Item eliminado", "info")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))


@main_bp.route("/rutinas/<int:rutina_id>/reorder", methods=["POST"])
@login_required
def rutina_reorder(rutina_id: int):
    if not is_admin():
        return jsonify({"ok": False, "error": "Solo admin"}), 403

    if not hasattr(RutinaItem, "posicion"):
        return jsonify({"ok": False, "error": "Tu modelo/DB no tiene columna 'posicion'."}), 400

    data = request.get_json(silent=True) or {}
    order = data.get("order") or []

    if not isinstance(order, list) or not order:
        return jsonify({"ok": False, "error": "order inválido"}), 400

    items = RutinaItem.query.filter(
        RutinaItem.rutina_id == rutina_id,
        RutinaItem.id.in_(order)
    ).all()
    by_id = {it.id: it for it in items}

    for idx, item_id in enumerate(order):
        try:
            iid = int(item_id)
        except Exception:
            continue
        it = by_id.get(iid)
        if it:
            it.posicion = idx

    db.session.commit()
    return jsonify({"ok": True})
