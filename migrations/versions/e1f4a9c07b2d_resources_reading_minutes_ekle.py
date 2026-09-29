"""resources reading_minutes ekle

Revision ID: e1f4a9c07b2d
Revises: c4d9a6b1e2f3
Create Date: 2026-09-30 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f4a9c07b2d'
down_revision: Union[str, Sequence[str], None] = 'c4d9a6b1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_WORDS_PER_MINUTE = 200  # Migration'lar uygulama kodundan bagimsiz kalsin diye formul burada dondurulmustur.


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'resources',
        sa.Column('reading_minutes', sa.Integer(), nullable=False, server_default='0'),
    )
    # Mevcut kayitlar icin geri dolum (full_text yoksa icerik metninden).
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, full_text, content FROM resources")).fetchall()
    for resource_id, full_text, content in rows:
        words = len((full_text or content or "").split())
        if words:
            minutes = max(1, round(words / _WORDS_PER_MINUTE))
            bind.execute(
                sa.text("UPDATE resources SET reading_minutes = :m WHERE id = :i"),
                {"m": minutes, "i": resource_id},
            )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('resources') as batch_op:
        batch_op.drop_column('reading_minutes')
