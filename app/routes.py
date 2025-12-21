# app/routes.py
from __future__ import annotations

"""
Este archivo NO define un Blueprint.
Solo expone `main_bp` importándolo desde app.blueprints
y fuerza la importación de los módulos para que registren rutas.
"""

from app.blueprints import bp as main_bp

# Importa módulos (registran endpoints sobre bp)
from app.blueprints import auth      # noqa: F401
from app.blueprints import coach     # noqa: F401
from app.blueprints import athlete   # noqa: F401
from app.blueprints import routines  # noqa: F401
from app.blueprints import tabata    # noqa: F401
from app.blueprints import media     # noqa: F401
from app.blueprints import ai        # noqa: F401
