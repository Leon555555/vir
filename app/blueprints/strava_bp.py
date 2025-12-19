# app/blueprints/strava_bp.py
from __future__ import annotations

import os
import secrets
from datetime import datetime

from flask import Blueprint, redirect, request, url_for, flash, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models_strava import IntegrationAccount
from app.integrations.strava_client import exchange_code_for_token
from app.integrations.strava_sync import sync_latest_activities


strava_bp = Blueprint("strava", __name__, url_prefix="/strava")


@strava_bp.get("/connect")
@login_required
def connect():
    client_id = os.getenv("STRAVA_CLIENT_ID")
    redirect_uri = os.getenv("STRAVA_REDIRECT_URI")  # debe ser tu /strava/callback

    if not client_id or not redirect_uri:
        flash("Faltan variables STRAVA_CLIENT_ID / STRAVA_REDIRECT_URI", "danger")
        return redirect(url_for("main.perfil"))

    state = secrets.token_urlsafe(16)

    scope = "read,activity:read_all"
    approve_prompt = "auto"

    authorize_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&approval_prompt={approve_prompt}"
        f"&scope={scope}"
        f"&state={state}"
    )

    return redirect(authorize_url)


@strava_bp.get("/callback")
@login_required
def callback():
    err = request.args.get("error")
    if err:
        flash(f"Strava canceló la autorización: {err}", "warning")
        return redirect(url_for("main.perfil"))

    code = request.args.get("code")
    if not code:
        flash("No llegó el code de Strava.", "danger")
        return redirect(url_for("main.perfil"))

    try:
        token_data = exchange_code_for_token(code)
    except Exception as e:
        current_app.logger.exception("Error intercambiando code por token")
        flash(f"Error conectando con Strava: {e}", "danger")
        return redirect(url_for("main.perfil"))

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_at = token_data.get("expires_at")
    athlete = token_data.get("athlete") or {}
    external_user_id = str(athlete.get("id") or "")

    if not access_token or not refresh_token or not expires_at:
        flash("Respuesta inválida de Strava (faltan tokens).", "danger")
        return redirect(url_for("main.perfil"))

    acc = IntegrationAccount.query.filter_by(
        user_id=current_user.id,
        provider="strava"
    ).first()

    if not acc:
        acc = IntegrationAccount(
            user_id=current_user.id,
            provider="strava",
        )
        db.session.add(acc)

    acc.external_user_id = external_user_id or None
    acc.access_token = access_token
    acc.refresh_token = refresh_token
    acc.expires_at = int(expires_at)
    acc.updated_at = datetime.utcnow()

    db.session.commit()

    # Sync automático (opcional)
    try:
        sync_latest_activities(current_user.id)
    except Exception:
        current_app.logger.exception("Sync falló, pero la vinculación quedó hecha")
        flash("Strava vinculado ✅ (pero el sync falló, probá 'Sincronizar ahora').", "warning")
        return redirect(url_for("main.perfil"))

    flash("Strava vinculado ✅ y sincronizado.", "success")
    return redirect(url_for("main.perfil"))


@strava_bp.get("/sync")
@login_required
def sync_now():
    try:
        sync_latest_activities(current_user.id)
        flash("Sincronización completada ✅", "success")
    except Exception as e:
        current_app.logger.exception("Error sincronizando Strava")
        flash(f"Error sincronizando: {e}", "danger")

    return redirect(url_for("main.perfil"))
