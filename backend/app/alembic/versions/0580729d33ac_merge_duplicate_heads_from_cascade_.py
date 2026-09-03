"""merge duplicate heads from cascade-delete branch

Revision ID: 0580729d33ac
Revises: fe56fa70289e, b1c2d3e4f5a6
Create Date: 2026-09-03 18:37:24.104764

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '0580729d33ac'
down_revision = ('b1c2d3e4f5a6', 'fe56fa70289e')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
