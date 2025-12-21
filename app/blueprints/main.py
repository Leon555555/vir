# app/blueprints/main.py
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("main", __name__)

@bp.get("/health")
def health():
    return {"ok": True}
