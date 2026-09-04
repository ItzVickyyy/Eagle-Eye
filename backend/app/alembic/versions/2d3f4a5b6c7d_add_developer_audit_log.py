"""Add Developer audit log table

Revision ID: 2d3f4a5b6c7d
Revises: e5f6a7b8c9d0
Create Date: 2026-09-04 15:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2d3f4a5b6c7d"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auditlog",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("component", sa.String(length=50), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("actor_role", sa.String(length=50), nullable=True),
        sa.Column("actor_is_developer", sa.Boolean(), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("message", sa.String(length=2048), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auditlog_created_at"), "auditlog", ["created_at"], unique=False)
    op.create_index(op.f("ix_auditlog_event"), "auditlog", ["event"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auditlog_event"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_created_at"), table_name="auditlog")
    op.drop_table("auditlog")