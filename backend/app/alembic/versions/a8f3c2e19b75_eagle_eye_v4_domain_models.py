"""Eagle Eye domain models — v4 reconciliation

Revision ID: a8f3c2e19b75
Revises: 1a31ce608336
Create Date: 2026-09-03 00:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "a8f3c2e19b75"
down_revision = "1a31ce608336"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "role",
            sa.Enum("super_admin", "admin", "contributor", name="userrole"),
            nullable=False,
            server_default="contributor",
        ),
    )
    op.add_column(
        "user",
        sa.Column("department", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("position_title", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    )

    op.drop_table("item")

    op.create_table(
        "category",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("slug", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_category_slug"), "category", ["slug"], unique=True)

    op.create_table(
        "tag",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_tag_name"), "tag", ["name"], unique=True)

    op.create_table(
        "article",
        sa.Column("headline", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("slug", sqlmodel.sql.sqltypes.AutoString(length=550), nullable=False),
        sa.Column("excerpt", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("cover_image_url", sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "pending", "published", "archived", name="articlestatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("views_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("date_published", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_article_slug"), "article", ["slug"], unique=True)

    op.create_table(
        "articletag",
        sa.Column("article_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["article.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("article_id", "tag_id"),
    )

    op.create_table(
        "media",
        sa.Column("file_url", sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=False),
        sa.Column("file_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("article_id", sa.UUID(), nullable=True),
        sa.Column("uploaded_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["article.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "clubmember",
        sa.Column("first_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("last_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("position", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("position_title", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("department", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("photo_url", sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=True),
        sa.Column("is_officer", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "contactmessage",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("subject", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("new", "read", name="contactmessagestatus"),
            nullable=False,
            server_default="new",
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sitesetting",
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("sitesetting")
    op.drop_table("contactmessage")
    op.drop_table("clubmember")
    op.drop_table("media")
    op.drop_table("articletag")
    op.drop_table("article")
    op.drop_index(op.f("ix_tag_name"), table_name="tag")
    op.drop_table("tag")
    op.drop_index(op.f("ix_category_slug"), table_name="category")
    op.drop_table("category")

    op.create_table(
        "item",
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.drop_column("user", "position_title")
    op.drop_column("user", "department")
    op.drop_column("user", "role")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS articlestatus")
    op.execute("DROP TYPE IF EXISTS contactmessagestatus")
