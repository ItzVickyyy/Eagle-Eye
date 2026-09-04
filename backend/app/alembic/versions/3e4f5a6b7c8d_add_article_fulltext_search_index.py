"""Add article full-text search GIN index

Revision ID: 3e4f5a6b7c8d
Revises: 2d3f4a5b6c7d
Create Date: 2026-09-04 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3e4f5a6b7c8d"
down_revision = "2d3f4a5b6c7d"
branch_labels = None
depends_on = None

# The searchable document, shared between the migration index and the runtime
# query in app/api/routes/articles.py. Kept in sync textually so PostgreSQL can
# use the functional index for `to_tsvector(...) @@ websearch_to_tsquery(...)`.
#
# `regexp_replace` strips HTML markup from the sanitized article body at
# index/search time only; the write-time sanitization pipeline is untouched.
#
# Note: `concat_ws` is marked STABLE by PostgreSQL and is therefore NOT
# permitted in index expressions. We must use the IMMUTABLE `||` string
# concatenation operator instead so the functional GIN index is accepted.
DOC_EXPRESSION = sa.text(
    "to_tsvector('english', regexp_replace("
    "coalesce(headline, '') || ' ' || "
    "coalesce(excerpt, '') || ' ' || "
    "coalesce(body, ''), '<[^>]+>', '', 'g'))"
)


def upgrade() -> None:
    op.create_index(
        "ix_article_search_gin",
        "article",
        [DOC_EXPRESSION],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_article_search_gin", table_name="article")
