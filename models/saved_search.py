from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SavedSearch(Base):
    """Makale Market'te kaydedilmis arama (konu + filtreler) ve yeni yayin takibi durumu.

    `seen_ids`: kullanicinin bu aramada gordugu OpenAlex kimlikleri; son kontrolde bunlarin
    disinda kalan yayinlar `new_count` olarak sayilir (bkz. services/saved_search_service.py).
    """

    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False, default="")
    filters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    tag_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seen_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    new_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    def __repr__(self) -> str:
        return f"<SavedSearch id={self.id} topic={self.topic!r}>"
