"""saved_searches tablosu ekle

Revision ID: c4d9a6b1e2f3
Revises: 8b3f1c2d9a47
Create Date: 2026-09-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d9a6b1e2f3'
down_revision: Union[str, Sequence[str], None] = '8b3f1c2d9a47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'saved_searches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('topic', sa.Text(), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=False),
        sa.Column('tag_name', sa.String(length=100), nullable=True),
        sa.Column('seen_ids', sa.JSON(), nullable=False),
        sa.Column('new_count', sa.Integer(), nullable=False),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('saved_searches')
