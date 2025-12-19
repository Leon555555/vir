# app/utils/media.py
from __future__ import annotations

import os
import time
from typing import Optional

from flask import current_app, url_for
from werkzeug.utils import secure_filename

ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".webm"}


def ensure_static_videos_dir() -> str:
    """Crea /static/videos si no existe y devuelve path absoluto."""
    videos_dir = os.path.join(current_app.static_folder, "videos")
    os.makedirs(videos_dir, exist_ok=True)
    return videos_dir


def save_uploaded_video(file_storage) -> Optional[str]:
    """
    Guarda el video dentro de /static/videos.
    Devuelve el path relativo que se guarda en DB:  videos/<archivo.mp4>
    """
    if not file_storage or not getattr(file_storage, "filename", ""):
        return None

    filename = secure_filename(file_storage.filename)
    name, ext = os.path.splitext(filename)
    ext = (ext or "").lower()

    if ext not in ALLOWED_VIDEO_EXT:
        raise ValueError("Formato no permitido. Usá .mp4, .mov o .webm")

    # Render/Linux es case-sensitive → normalizamos y evitamos colisiones
    safe_name = f"{name.strip().lower()}_{int(time.time())}{ext}"

    videos_dir = ensure_static_videos_dir()
    abs_path = os.path.join(videos_dir, safe_name)
    file_storage.save(abs_path)

    return f"videos/{safe_name}"


def normalize_video_relpath(video_url: Optional[str]) -> Optional[str]:
    """
    Acepta:
      - 'videos/archivo.mp4'
      - 'archivo.mp4' (lo corrige a videos/archivo.mp4)
      - '/static/videos/archivo.mp4' (lo normaliza)
    Devuelve SIEMPRE: 'videos/archivo.mp4' o None
    """
    if not video_url:
        return None

    v = str(video_url).strip()

    # si alguien guardó URL completa
    if v.startswith("/static/"):
        v = v.replace("/static/", "", 1)

    # si viene solo el filename
    if "/" not in v:
        v = f"videos/{v}"

    return v


def video_src(video_url: Optional[str]) -> Optional[str]:
    """Devuelve URL final lista para el front: /static/videos/..."""
    rel = normalize_video_relpath(video_url)
    if not rel:
        return None
    return url_for("static", filename=rel)
