# app/routes/media.py
from __future__ import annotations

from flask import redirect, url_for, flash, request
from flask_login import login_required

from app.extensions import db
from app.models import Ejercicio

from . import main_bp, is_admin, list_repo_videos, save_video_to_static


@main_bp.route("/admin/ejercicios/nuevo", methods=["POST"])
@login_required
def admin_nuevo_ejercicio():
    """
    MODO GRATIS:
    - En producción (Render), NO dependas de subir archivos al server.
    - Elegí un archivo existente en app/static/videos (commiteado).
    """
    if not is_admin():
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
            flash("⚠️ Video subido al server (Render gratis puede perderse). Ideal: seleccionar existente.", "warning")
        except Exception as e:
            flash(f"Error subiendo video: {e}", "danger")
            return redirect(url_for("main.dashboard_entrenador"))
    else:
        flash("Falta video: seleccioná uno existente o subí uno (local).", "danger")
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
