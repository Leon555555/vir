# app/routes/ai.py
from __future__ import annotations

from flask import jsonify, request
from flask_login import login_required

from . import main_bp, is_admin


@main_bp.route("/ai/session_script", methods=["POST"])
@login_required
def ai_session_script():
    """
    Endpoint simple para no romper tu perfil.html actual.
    Si ya tenías IA real, la pegamos acá después.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    fecha = data.get("fecha")

    # Si querés que solo admin pueda, activalo:
    # if not is_admin(): return jsonify({"ok": False, "error": "Solo admin"}), 403

    script = f"Guión del día ({fecha}):\n- Activación\n- Bloque principal\n- Enfriamiento\n\n(placeholder IA)"

    return jsonify({"ok": True, "script": script})
