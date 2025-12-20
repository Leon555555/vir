# app/schema_fix.py
from __future__ import annotations

import os
from sqlalchemy import text

from app.extensions import db


def _table_exists(table: str) -> bool:
    q = text("SELECT to_regclass(:t)")
    return db.session.execute(q, {"t": f"public.{table}"}).scalar() is not None


def _sql_exec(sql: str):
    try:
        db.session.execute(text(sql))
        db.session.commit()
        print("✅ SQL OK:", " ".join(sql.strip().split()))
    except Exception as e:
        db.session.rollback()
        print("❌ SQL ERROR:", str(e))


def fix_schema() -> None:
    """
    Fix incremental del esquema SIN migraciones y SIN CLI.
    Corre ALTER TABLE IF NOT EXISTS para columnas/fk que falten.
    """

    # users columns
    if _table_exists("users"):
        _sql_exec("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
        _sql_exec("ALTER TABLE users ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW();")

    # dia_plan FK (limpia huérfanos antes)
    if _table_exists("dia_plan"):
        _sql_exec("""
            DELETE FROM dia_plan dp
            WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = dp.user_id);
        """)
        _sql_exec("ALTER TABLE dia_plan DROP CONSTRAINT IF EXISTS dia_plan_user_id_fkey;")
        _sql_exec("""
            ALTER TABLE dia_plan
            ADD CONSTRAINT dia_plan_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE;
        """)

    # athlete_logs FK
    if _table_exists("athlete_logs"):
        _sql_exec("ALTER TABLE athlete_logs DROP CONSTRAINT IF EXISTS athlete_logs_user_id_fkey;")
        _sql_exec("""
            ALTER TABLE athlete_logs
            ADD CONSTRAINT athlete_logs_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE;
        """)

    # athlete_checks FK
    if _table_exists("athlete_checks"):
        _sql_exec("ALTER TABLE athlete_checks DROP CONSTRAINT IF EXISTS athlete_checks_user_id_fkey;")
        _sql_exec("""
            ALTER TABLE athlete_checks
            ADD CONSTRAINT athlete_checks_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE;
        """)

    # STRAVA: columnas faltantes
    if _table_exists("integration_accounts"):
        _sql_exec("ALTER TABLE integration_accounts ADD COLUMN IF NOT EXISTS external_user_id VARCHAR(80);")

    if _table_exists("external_activities"):
        _sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS start_date TIMESTAMP;")
        _sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS distance_m DOUBLE PRECISION;")
        _sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS moving_time_s INTEGER;")
        _sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS elapsed_time_s INTEGER;")
        _sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS raw_json JSON;")
        _sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();")
        _sql_exec("ALTER TABLE external_activities ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();")

    # ✅ RUTINAS: columnas que te faltan y están rompiendo /builder
    if _table_exists("rutina_items"):
        _sql_exec("ALTER TABLE rutina_items ADD COLUMN IF NOT EXISTS peso VARCHAR(40);")
        _sql_exec("ALTER TABLE rutina_items ADD COLUMN IF NOT EXISTS posicion INTEGER;")
        _sql_exec("CREATE INDEX IF NOT EXISTS ix_rutina_items_rutina_id ON rutina_items (rutina_id);")
        _sql_exec("CREATE INDEX IF NOT EXISTS ix_rutina_items_posicion ON rutina_items (posicion);")


def maybe_run_schema_fix(app) -> None:
    """
    Lo corremos SIEMPRE en Render (o cuando quieras), sin depender de run.py.
    """
    is_prod = os.getenv("RENDER") == "1" or os.getenv("FLASK_ENV") == "production"
    if not is_prod:
        # En local podés cambiar esto si querés que corra también.
        return

    with app.app_context():
        fix_schema()
