"""add review_assignments table

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-09-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'reviewassignment',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('article_id', sa.UUID(), nullable=False),
        sa.Column('reviewer_id', sa.UUID(), nullable=False),
        sa.Column('assigned_by', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('notes', sa.String(length=2000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['article.id'], name='fk_reviewassignment_article_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['user.id'], name='fk_reviewassignment_assigned_by', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['user.id'], name='fk_reviewassignment_reviewer_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reviewassignment_article_id', 'reviewassignment', ['article_id'])
    op.create_index('ix_reviewassignment_reviewer_id', 'reviewassignment', ['reviewer_id'])
    op.create_index('ix_reviewassignment_assigned_by', 'reviewassignment', ['assigned_by'])
    op.create_index('ix_reviewassignment_status', 'reviewassignment', ['status'])


def downgrade():
    op.drop_index('ix_reviewassignment_status', table_name='reviewassignment')
    op.drop_index('ix_reviewassignment_assigned_by', table_name='reviewassignment')
    op.drop_index('ix_reviewassignment_reviewer_id', table_name='reviewassignment')
    op.drop_index('ix_reviewassignment_article_id', table_name='reviewassignment')
    op.drop_table('reviewassignment')
