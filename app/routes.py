# app/routes.py
from __future__ import annotations

# ✅ Importa el blueprint principal desde app/blueprints
# app/routes.py
from __future__ import annotations

# ✅ Blueprint real
from app.blueprints import bp as main_bp

# ✅ Importar módulos para registrar endpoints en main_bp
from app.blueprints import athlete   # noqa: F401
from app.blueprints import routines  # noqa: F401
from app.blueprints import tabata    # noqa: F401
from app.blueprints import media     # noqa: F401

# (si existen en tu proyecto, mantenelos)
try:
    from app.blueprints import auth   # noqa: F401
except Exception:
    pass

try:
    from app.blueprints import coach  # noqa: F401
except Exception:
    pass

try:
    from app.blueprints import ai     # noqa: F401
except Exception:
    pass
