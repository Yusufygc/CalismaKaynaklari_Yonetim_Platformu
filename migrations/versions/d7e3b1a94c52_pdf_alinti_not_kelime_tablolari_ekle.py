"""pdf_annotations, pdf_page_notes ve pdf_terms tablolari ekle

Revision ID: d7e3b1a94c52
Revises: b3a91c5d7e20
Create Date: 2026-10-12 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e3b1a94c52'
down_revision: Union[str, Sequence[str], None] = 'b3a91c5d7e20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'pdf_annotations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uid', sa.String(length=26), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('label_key', sa.String(length=24), nullable=False),
        sa.Column('color', sa.String(length=30), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('quote_exact', sa.Text(), nullable=False),
        sa.Column('quote_prefix', sa.String(length=128), nullable=True),
        sa.Column('quote_suffix', sa.String(length=128), nullable=True),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('segments', sa.JSON(), nullable=False),
        sa.Column('engine_fp', sa.String(length=64), nullable=True),
        sa.Column('anchor_status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('legacy_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['pdf_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uid'),
        sa.UniqueConstraint('legacy_id'),
    )
    op.create_index(op.f('ix_pdf_annotations_document_id'), 'pdf_annotations', ['document_id'], unique=False)
    op.create_index(op.f('ix_pdf_annotations_page'), 'pdf_annotations', ['page'], unique=False)

    op.create_table(
        'pdf_page_notes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uid', sa.String(length=26), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('page', sa.Integer(), nullable=False),
        sa.Column('x', sa.Float(), nullable=False),
        sa.Column('y', sa.Float(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('legacy_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['pdf_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uid'),
        sa.UniqueConstraint('legacy_id'),
    )
    op.create_index(op.f('ix_pdf_page_notes_document_id'), 'pdf_page_notes', ['document_id'], unique=False)

    op.create_table(
        'pdf_terms',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uid', sa.String(length=26), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('word', sa.String(length=200), nullable=False),
        sa.Column('translation', sa.String(length=200), nullable=False),
        sa.Column('context_sentence', sa.Text(), nullable=True),
        sa.Column('mastery_level', sa.Integer(), nullable=False),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('segments', sa.JSON(), nullable=False),
        sa.Column('engine_fp', sa.String(length=64), nullable=True),
        sa.Column('anchor_status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('legacy_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['pdf_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uid'),
        sa.UniqueConstraint('legacy_id'),
    )
    op.create_index(op.f('ix_pdf_terms_document_id'), 'pdf_terms', ['document_id'], unique=False)
    op.create_index(op.f('ix_pdf_terms_page'), 'pdf_terms', ['page'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_pdf_terms_page'), table_name='pdf_terms')
    op.drop_index(op.f('ix_pdf_terms_document_id'), table_name='pdf_terms')
    op.drop_table('pdf_terms')
    op.drop_index(op.f('ix_pdf_page_notes_document_id'), table_name='pdf_page_notes')
    op.drop_table('pdf_page_notes')
    op.drop_index(op.f('ix_pdf_annotations_page'), table_name='pdf_annotations')
    op.drop_index(op.f('ix_pdf_annotations_document_id'), table_name='pdf_annotations')
    op.drop_table('pdf_annotations')
