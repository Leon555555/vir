# app/blueprints/strava_bp.py
from __future__ import annotations

import os
from datetime import datetime

from flask import Blueprint, redirect, url_for, request, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models_strava import IntegrationAccount
from app.integrations.strava_client import exchange_code_for_token
from app.integrations.strava_sync import sync_latest_activities

strava_bp = Blueprint("strava", __name__, url_prefix="/strava")


@strava_bp.route("/connect")
@login_required
def connect():
    client_id = os.getenv("STRAVA_CLIENT_ID")
    redirect_uri = os.getenv("STRAVA_REDIRECT_URI")

    if not client_id or not redirect_uri:
        flash("⚠️ Faltan STRAVA_CLIENT_ID o STRAVA_REDIRECT_URI en variables de entorno.", "danger")
        return redirect(url_for("main.perfil_redirect"))

    scope = "read,activity:read_all"

    approve_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&approval_prompt=auto"
        f"&scope={scope}"
    )
    return redirect(approve_url)


@strava_bp.route("/callback")
@login_required
def callback():
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        flash(f"⚠️ Strava cancelado: {error}", "warning")
        return redirect(url_for("main.perfil_redirect"))

    if not code:
        flash("⚠️ No llegó el 'code' de Strava.", "danger")
        return redirect(url_for("main.perfil_redirect"))

    try:
        data = exchange_code_for_token(code)

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_at = int(data.get("expires_at") or 0)
        athlete = data.get("athlete") or {}
        external_user_id = str(athlete.get("id") or "") if athlete.get("id") else None

        if not access_token:
            flash("⚠️ Strava no devolvió access_token.", "danger")
            return redirect(url_for("main.perfil_redirect"))

        acc = IntegrationAccount.query.filter_by(user_id=current_user.id, provider="strava").first()
        if not acc:
            acc = IntegrationAccount(user_id=current_user.id, provider="strava")
            db.session.add(acc)

        acc.external_user_id = external_user_id
        acc.access_token = access_token
        acc.refresh_token = refresh_token
        acc.expires_at = expires_at
        acc.updated_at = datetime.utcnow()

        db.session.commit()

        # Sync no debe romper el flujo si falla
        try:
            inserted = sync_latest_activities(current_user.id, per_page=30)
            flash(f"✅ Strava vinculado. Actividades nuevas: {inserted}", "success")
        except Exception as e:
            flash(f"✅ Strava vinculado ✅ (pero el sync falló: {e}). Probá 'Sincronizar ahora'.", "warning")

        return redirect(url_for("main.perfil_redirect"))

    except Exception as e:
        db.session.rollback()
        flash(f"⚠️ Error vinculando Strava: {e}", "danger")
        return redirect(url_for("main.perfil_redirect"))
