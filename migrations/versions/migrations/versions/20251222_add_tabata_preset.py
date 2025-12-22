"""add tabata_preset to rutinas

Revision ID: 20251222_add_tabata_preset
Revises: <PONE_AQUI_TU_REVISION_ANTERIOR>
Create Date: 2025-12-22 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251222_add_tabata_preset"
down_revision = "<PONE_AQUI_TU_REVISION_ANTERIOR>"
branch_labels = None
depends_on = None


def upgrade():
    # En Postgres: JSONB. En otros: cae a JSON/Text según dialecto.
    # Usamos JSON (SQLAlchemy) que en Postgres lo mapeará correctamente en muchos casos.
    # Si querés 100% JSONB, lo hacemos con sa.dialects.postgresql.JSONB.
    try:
        from sqlalchemy.dialects import postgresql
        coltype = postgresql.JSONB(astext_type=sa.Text())
    except Exception:
        coltype = sa.JSON()

    op.add_column("rutinas", sa.Column("tabata_preset", coltype, nullable=True))


def downgrade():
    op.drop_column("rutinas", "tabata_preset")
