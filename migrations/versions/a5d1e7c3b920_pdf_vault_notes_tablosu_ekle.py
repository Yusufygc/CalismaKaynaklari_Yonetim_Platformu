"""pdf_vault_notes tablosu ekle

Revision ID: a5d1e7c3b920
Revises: f2c8d4a61b93
Create Date: 2026-10-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5d1e7c3b920'
down_revision: Union[str, Sequence[str], None] = 'f2c8d4a61b93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'pdf_vault_notes',
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('citekey', sa.String(length=80), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['pdf_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('document_id'),
        sa.UniqueConstraint('citekey'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('pdf_vault_notes')
