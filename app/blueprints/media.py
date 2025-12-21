# app/blueprints/media.py
from __future__ import annotations

from datetime import datetime
from flask import jsonify
from . import bp

@bp.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})
