"""highlights start_index length ekle

Revision ID: 1f6c2de78d90
Revises: 73989d002a5c
Create Date: 2026-09-29 01:00:28.603280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f6c2de78d90'
down_revision: Union[str, Sequence[str], None] = '73989d002a5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('highlights', sa.Column('start_index', sa.Integer(), nullable=True))
    op.add_column('highlights', sa.Column('length', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('highlights', 'length')
    op.drop_column('highlights', 'start_index')
