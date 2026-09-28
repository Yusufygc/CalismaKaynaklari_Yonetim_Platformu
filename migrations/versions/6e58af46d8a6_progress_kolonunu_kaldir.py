"""progress kolonunu kaldir

Revision ID: 6e58af46d8a6
Revises: ff016ad9bf6e
Create Date: 2026-07-06 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e58af46d8a6'
down_revision: Union[str, Sequence[str], None] = 'ff016ad9bf6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('resources') as batch_op:
        batch_op.drop_column('progress')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('resources') as batch_op:
        batch_op.add_column(
            sa.Column('progress', sa.Float(), nullable=False, server_default='0')
        )
