"""eski pdf_notes tablosunu (bossa) kaldir

pdfkit sayfa notlarini `pdf_page_notes` tablosunda tutuyor; eski `pdf_notes` tablosu artik hicbir kod tarafindan
yazilmiyor. Tablo YALNIZ bossa silinir: icinde henuz pdfkit'e tasinmamis satir varsa (eski surumden dogrudan
yukseltilmis, PDF dosyalari henuz depoya alinmamis bir veritabani) tablo korunur ve calisma zamaninda
`LegacyAnnotationImporter` satirlari tasiyip tablo bosalinca tabloyu kendisi kaldirir. Kullanici verisi bu migration ile
asla silinmez (K13); uygulama migration oncesi zaten otomatik yedek alir.

Revision ID: c9f4e2b7a815
Revises: b7e3c5a91d04
Create Date: 2026-10-13 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9f4e2b7a815'
down_revision: Union[str, Sequence[str], None] = 'b7e3c5a91d04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if 'pdf_notes' not in sa.inspect(bind).get_table_names():
        return
    if bind.execute(sa.text('SELECT count(*) FROM pdf_notes')).scalar_one() == 0:
        op.drop_table('pdf_notes')


def downgrade() -> None:
    """Downgrade schema."""
    if 'pdf_notes' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'pdf_notes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=False),
        sa.Column('page', sa.Integer(), nullable=False),
        sa.Column('x', sa.Float(), nullable=False),
        sa.Column('y', sa.Float(), nullable=False),
        sa.Column('note_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['resource_id'], ['resources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
