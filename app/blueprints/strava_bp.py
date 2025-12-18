# app/blueprints/strava_bp.py
from __future__ import annotations

import os
import secrets

from flask import Blueprint, redirect, request, url_for, flash, session
from flask_login import login_required, current_user

from app.extensions import db
from app.models_strava import IntegrationAccount
from app.integrations.strava_client import get_strava_client, StravaError
from app.integrations.strava_sync import sync_latest_activities

strava_bp = Blueprint("strava", __name__, url_prefix="/integrations/strava")


def _go_back():
    """
    Tu app usa /perfil/<id> (lo vimos en logs).
    Esto evita depender de un endpoint específico tipo main.perfil.
    """
    return redirect(f"/perfil/{current_user.id}")


@strava_bp.get("/connect")
@login_required
def connect():
    redirect_uri = os.getenv("STRAVA_REDIRECT_URI", "").strip()
    if not redirect_uri:
        flash("Falta STRAVA_REDIRECT_URI en Render (Environment).", "danger")
        return _go_back()

    state = secrets.token_urlsafe(24)
    session["strava_oauth_state"] = state

    client = get_strava_client()
    auth_url = client.build_authorize_url(
        redirect_uri=redirect_uri,
        state=state,
        scope="read,activity:read_all",
        approval_prompt="auto",
    )
    return redirect(auth_url)


@strava_bp.get("/callback")
@login_required
def callback():
    err = request.args.get("error")
    if err:
        flash(f"Strava canceló la autorización: {err}", "warning")
        return _go_back()

    code = request.args.get("code")
    state = request.args.get("state")

    if not code or not state or state != session.get("strava_oauth_state"):
        flash("OAuth inválido (state mismatch).", "danger")
        return _go_back()

    client = get_strava_client()
    try:
        data = client.exchange_code(code)
    except StravaError as e:
        flash(f"Error Strava (token exchange): {e}", "danger")
        return _go_back()

    athlete = data.get("athlete") or {}
    provider_user_id = str(athlete.get("id")) if athlete.get("id") else None

    account = IntegrationAccount.query.filter_by(user_id=current_user.id, provider="strava").first()
    if account is None:
        account = IntegrationAccount(user_id=current_user.id, provider="strava")
        db.session.add(account)

    account.provider_user_id = provider_user_id
    account.access_token = data["access_token"]
    account.refresh_token = data["refresh_token"]
    account.expires_at = data["expires_at"]
    account.scope = data.get("scope")

    db.session.commit()

    flash("✅ Strava conectado correctamente.", "success")
    return _go_back()


@strava_bp.post("/sync")
@login_required
def sync():
    result = sync_latest_activities(current_user.id, per_page=50, max_pages=3)

    if not result.get("ok"):
        flash(f"Sync Strava falló: {result.get('error')}", "danger")
        return _go_back()

    flash(f"✅ Sync Strava OK — nuevas: {result['created']} | actualizadas: {result['updated']}", "success")
    return _go_back()
