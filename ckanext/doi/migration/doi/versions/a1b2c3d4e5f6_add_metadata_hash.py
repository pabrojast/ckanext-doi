"""Add metadata_hash column to doi table

Revision ID: a1b2c3d4e5f6
Revises: 9b4a4cd0c97b
Create Date: 2026-03-04 12:34:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9b4a4cd0c97b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('doi', sa.Column('metadata_hash', sa.types.UnicodeText, nullable=True))


def downgrade():
    op.drop_column('doi', 'metadata_hash')
