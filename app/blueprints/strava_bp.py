# app/blueprints/strava_bp.py
from __future__ import annotations

import os
import secrets

from flask import Blueprint, redirect, request, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models_strava import IntegrationAccount
from app.integrations.strava_client import get_strava_client
from app.integrations.strava_sync import sync_latest_activities

strava_bp = Blueprint("strava", __name__, url_prefix="/strava")


@strava_bp.route("/connect")
@login_required
def connect():
    client = get_strava_client()

    state = secrets.token_urlsafe(16)

    redirect_uri = os.getenv(
        "STRAVA_REDIRECT_URI",
        url_for("strava.callback", _external=True)
    )

    auth_url = client.build_authorize_url(
        redirect_uri=redirect_uri,
        state=state,
    )

    return redirect(auth_url)


@strava_bp.route("/callback")
@login_required
def callback():
    code = request.args.get("code")
    if not code:
        flash("Error al conectar con Strava", "danger")
        return redirect(url_for("main.dashboard"))

    client = get_strava_client()
    data = client.exchange_code(code)

    account = IntegrationAccount.query.filter_by(
        user_id=current_user.id,
        provider="strava"
    ).first()

    if not account:
        account = IntegrationAccount(
            user_id=current_user.id,
            provider="strava"
        )
        db.session.add(account)

    account.access_token = data["access_token"]
    account.refresh_token = data["refresh_token"]
    account.expires_at = data["expires_at"]
    account.scope = data.get("scope")

    db.session.commit()

    # Sincronizamos automáticamente
    sync_latest_activities(current_user.id)

    flash("Strava conectado correctamente ✅", "success")
    return redirect(url_for("main.dashboard"))
