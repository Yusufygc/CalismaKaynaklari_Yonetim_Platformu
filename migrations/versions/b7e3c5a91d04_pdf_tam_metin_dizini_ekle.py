"""pdf_text_index tablosu ve pdf_page_fts (FTS5) ekle

Revision ID: b7e3c5a91d04
Revises: a5d1e7c3b920
Create Date: 2026-10-13 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from sqlalchemy.exc import OperationalError


# revision identifiers, used by Alembic.
revision: str = 'b7e3c5a91d04'
down_revision: Union[str, Sequence[str], None] = 'a5d1e7c3b920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'pdf_text_index',
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=12), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['pdf_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('document_id'),
    )
    # FTS5 bu SQLite derlemesinde yoksa tablo olusturulmaz; uygulama aramasiz calisir (bkz. PageIndexRepository.available).
    try:
        op.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS pdf_page_fts USING fts5("
            "folded, original UNINDEXED, tokenize='unicode61 remove_diacritics 2')"
        )
    except OperationalError:
        pass


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS pdf_page_fts")
    op.drop_table('pdf_text_index')
