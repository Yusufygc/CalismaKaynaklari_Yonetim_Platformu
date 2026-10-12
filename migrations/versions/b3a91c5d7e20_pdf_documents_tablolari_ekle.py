"""pdf_documents ve pdf_resource_documents tablolari ekle

Revision ID: b3a91c5d7e20
Revises: e1f4a9c07b2d
Create Date: 2026-10-12 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3a91c5d7e20'
down_revision: Union[str, Sequence[str], None] = 'e1f4a9c07b2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'pdf_documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('rel_path', sa.String(length=512), nullable=False),
        sa.Column('byte_size', sa.BigInteger(), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False),
        sa.Column('has_text_layer', sa.Boolean(), nullable=False),
        sa.Column('pdf_title', sa.String(length=500), nullable=True),
        sa.Column('pdf_author', sa.String(length=500), nullable=True),
        sa.Column('doi', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sha256'),
    )
    op.create_index(op.f('ix_pdf_documents_doi'), 'pdf_documents', ['doi'], unique=False)
    op.create_table(
        'pdf_resource_documents',
        sa.Column('resource_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['pdf_documents.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('resource_id'),
    )
    op.create_index(
        op.f('ix_pdf_resource_documents_document_id'), 'pdf_resource_documents', ['document_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_pdf_resource_documents_document_id'), table_name='pdf_resource_documents')
    op.drop_table('pdf_resource_documents')
    op.drop_index(op.f('ix_pdf_documents_doi'), table_name='pdf_documents')
    op.drop_table('pdf_documents')
