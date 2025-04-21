"""add realizado

Revision ID: 19196d2e6f9f
Revises: 
Create Date: 2025-04-20 14:33:42.827216

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '19196d2e6f9f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('entrenamiento', sa.Column('realizado', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('entrenamiento', 'realizado')
