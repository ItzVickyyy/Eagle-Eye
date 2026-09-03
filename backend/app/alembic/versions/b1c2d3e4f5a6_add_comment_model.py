"""Add Comment model

Revision ID: b1c2d3e4f5a6
Revises: a8f3c2e19b75
Create Date: 2026-09-03 01:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "a8f3c2e19b75"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comment",
        sa.Column("guest_name", sqlmodel.sql.sqltypes.AutoString(length=150), nullable=False),
        sa.Column("guest_email", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "spam", name="commentstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["article.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("comment")
    op.execute("DROP TYPE IF EXISTS commentstatus")
