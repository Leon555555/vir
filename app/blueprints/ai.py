# app/blueprints/ai.py
from __future__ import annotations

from flask import request, jsonify
from flask_login import login_required

from app.models import User, DiaPlan
from . import bp
from ._shared import safe_parse_ymd

@bp.route("/ai/session_script", methods=["POST"])
@login_required
def ai_session_script():
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id") or 0)
    fecha = safe_parse_ymd(data.get("fecha", ""))

    if not user_id:
        return jsonify({"ok": False, "error": "Falta user_id"}), 400

    user = User.query.get(user_id)
    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()

    # Generador simple (placeholder) — después lo hacemos pro
    script = []
    script.append(f"📌 {fecha.isoformat()} — Sesión")
    if user:
        script.append(f"Atleta: {user.nombre}")
    if plan:
        script.append(f"Tipo: {plan.plan_type or '—'}")
        if plan.warmup:
            script.append(f"\n🔥 Activación:\n- {plan.warmup}")
        if plan.main:
            script.append(f"\n🏋️ Bloque principal:\n- {plan.main}")
        if plan.finisher:
            script.append(f"\n🧊 Enfriamiento:\n- {plan.finisher}")
    else:
        script.append("No hay plan cargado para este día.")

    script.append("\n✅ Objetivo: técnica limpia + constancia. Hidratación y pausa si hay dolor.")
    return jsonify({"ok": True, "script": "\n".join(script)})
