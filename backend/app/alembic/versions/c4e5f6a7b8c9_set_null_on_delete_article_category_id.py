"""Set NULL on delete for article category_id foreign key

Revision ID: c4e5f6a7b8c9
Revises: 0580729d33ac
Create Date: 2026-09-04 12:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "c4e5f6a7b8c9"
down_revision = "0580729d33ac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("article_category_id_fkey", "article", type_="foreignkey")
    op.create_foreign_key(
        "article_category_id_fkey",
        "article",
        "category",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("article_category_id_fkey", "article", type_="foreignkey")
    op.create_foreign_key(
        "article_category_id_fkey",
        "article",
        "category",
        ["category_id"],
        ["id"],
    )
