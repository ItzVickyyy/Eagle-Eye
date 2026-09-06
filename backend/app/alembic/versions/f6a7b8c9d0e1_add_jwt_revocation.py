"""Add JWT revocation support: user.token_version and token_revocations table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-06 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "3e4f5a6b7c8d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Per-user token version. A single monotonically increasing counter
    #    on the user row; every token issued before the current value is
    #    rejected. Used for bulk session invalidation on password change /
    #    reset. Default 0 for existing rows so the column is NOT NULL
    #    without a separate data migration.
    op.add_column(
        "user",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # 2) Per-jti denylist. Used by ``POST /auth/logout`` to kill a single
    #    session without affecting the user's other devices. The ``jti``
    #    column is the primary key (one row per token). A secondary index
    #    on ``expires_at`` accelerates the startup GC pass.
    op.create_table(
        "token_revocations",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "reason",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'logout'"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_token_revocations_user_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("jti", name="pk_token_revocations"),
    )
    op.create_index(
        "ix_token_revocations_expires_at",
        "token_revocations",
        ["expires_at"],
    )
    op.create_index(
        "ix_token_revocations_user_id",
        "token_revocations",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_token_revocations_user_id", table_name="token_revocations")
    op.drop_index("ix_token_revocations_expires_at", table_name="token_revocations")
    op.drop_table("token_revocations")
    op.drop_column("user", "token_version")
