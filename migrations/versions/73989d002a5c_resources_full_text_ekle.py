"""resources full_text ekle

Revision ID: 73989d002a5c
Revises: 6e58af46d8a6
Create Date: 2026-07-06 21:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73989d002a5c'
down_revision: Union[str, Sequence[str], None] = '6e58af46d8a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('resources', sa.Column('full_text', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('resources', 'full_text')
