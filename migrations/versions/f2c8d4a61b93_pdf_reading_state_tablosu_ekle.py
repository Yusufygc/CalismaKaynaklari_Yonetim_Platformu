"""pdf_reading_state tablosu ekle

Revision ID: f2c8d4a61b93
Revises: d7e3b1a94c52
Create Date: 2026-10-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2c8d4a61b93'
down_revision: Union[str, Sequence[str], None] = 'd7e3b1a94c52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'pdf_reading_state',
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('last_page', sa.Integer(), nullable=False),
        sa.Column('loc_x', sa.Float(), nullable=False),
        sa.Column('loc_y', sa.Float(), nullable=False),
        sa.Column('zoom', sa.Float(), nullable=False),
        sa.Column('max_page', sa.Integer(), nullable=False),
        sa.Column('total_seconds', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['pdf_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('document_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('pdf_reading_state')
