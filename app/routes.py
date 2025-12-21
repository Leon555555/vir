# app/routes.py
# Solo importa los módulos para registrar rutas en el blueprint "main"

from app.blueprints import bp as main_bp

# importa módulos (registran endpoints sobre bp)
from app.blueprints import auth      # noqa
from app.blueprints import coach     # noqa
from app.blueprints import athlete   # noqa
from app.blueprints import routines  # noqa
from app.blueprints import tabata    # noqa
from app.blueprints import media     # noqa
from app.blueprints import ai        # noqa
