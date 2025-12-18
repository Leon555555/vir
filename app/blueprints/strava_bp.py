# app/blueprints/strava_bp.py
from __future__ import annotations

import os
import secrets

from flask import Blueprint, redirect, request, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models_strava import IntegrationAccount
from app.integrations.strava_client import build_authorize_url, exchange_code_for_token
from app.integrations.strava_sync import sync_latest_activities


strava_bp = Blueprint("strava", __name__, url_prefix="/strava")


@strava_bp.get("/connect")
@login_required
def connect():
    state = secrets.token_urlsafe(16)
    auth_url = build_authorize_url(state=state)
    return redirect(auth_url)


@strava_bp.get("/callback")
@login_required
def callback():
    if request.args.get("error"):
        flash("Strava canceló o devolvió error.", "warning")
        return redirect(_safe_dashboard_redirect())

    code = request.args.get("code")
    if not code:
        flash("No llegó el code de Strava.", "danger")
        return redirect(_safe_dashboard_redirect())

    data = exchange_code_for_token(code)

    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    expires_at = int(data["expires_at"])
    athlete = data.get("athlete") or {}
    athlete_id = athlete.get("id")

    acc = IntegrationAccount.query.filter_by(user_id=current_user.id, provider="strava").first()
    if not acc:
        acc = IntegrationAccount(user_id=current_user.id, provider="strava")
        db.session.add(acc)

    acc.access_token = access_token
    acc.refresh_token = refresh_token
    acc.expires_at = expires_at
    if athlete_id:
        acc.external_user_id = str(athlete_id)

    db.session.commit()

    try:
        synced = sync_latest_activities(current_user.id, per_page=30)
        flash(f"✅ Strava conectado. Actividades sincronizadas: {synced}", "success")
    except Exception as e:
        flash(f"⚠️ Strava conectado, pero falló la sync: {e}", "warning")

    return redirect(_safe_dashboard_redirect())


def _safe_dashboard_redirect():
    """
    Tu app a veces usa /coach/dashboard.
    Si no existe main.dashboard, no rompemos.
    """
    for endpoint in ("main.dashboard", "main.coach_dashboard", "main.panel_entrenador"):
        try:
            return redirect(url_for(endpoint))
        except Exception:
            continue
    return redirect("/")
