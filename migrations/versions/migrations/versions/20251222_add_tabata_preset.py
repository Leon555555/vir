"""add tabata_preset to rutinas

Revision ID: 20251222_add_tabata_preset
Revises: 19196d2e6f9f
Create Date: 2025-12-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20251222_add_tabata_preset"
down_revision = "19196d2e6f9f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rutinas", sa.Column("tabata_preset", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("rutinas", "tabata_preset")
