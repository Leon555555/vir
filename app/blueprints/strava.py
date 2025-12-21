# app/blueprints/strava.py
from __future__ import annotations

import os
from urllib.parse import urlencode

from flask import Blueprint, redirect, url_for, flash, request
from flask_login import login_required, current_user

strava_bp = Blueprint("strava", __name__)

@strava_bp.route("/connect")
@login_required
def connect():
    client_id = os.getenv("STRAVA_CLIENT_ID", "")
    redirect_uri = os.getenv("STRAVA_REDIRECT_URI", "")

    if not client_id or not redirect_uri:
        flash("Strava no está configurado (faltan STRAVA_CLIENT_ID / STRAVA_REDIRECT_URI).", "warning")
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "approval_prompt": "auto",
        "scope": "read,activity:read_all",
    }
    return redirect("https://www.strava.com/oauth/authorize?" + urlencode(params))

@strava_bp.route("/callback")
@login_required
def callback():
    code = request.args.get("code")
    if not code:
        flash("Strava: no llegó el code.", "danger")
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

    # ✅ Stub: no guardamos tokens todavía (pero no rompe)
    flash("✅ Strava callback recibido (pendiente guardar tokens).", "success")
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))
