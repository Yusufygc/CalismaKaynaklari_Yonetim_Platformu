from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class PdfDocumentRow(Base):
    """Icerik (SHA-256) ile tanimli PDF belgesi; ayni PDF tek satirdir."""

    __tablename__ = "pdf_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    rel_path: Mapped[str] = mapped_column(String(512), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    has_text_layer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pdf_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_author: Mapped[str | None] = mapped_column(String(500), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="local")
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())


class PdfResourceLinkRow(Base):
    """Kaynak -> belge baglantisi (bir kaynagin tek PDF'i; ayni PDF birden cok kaynakta olabilir)."""

    __tablename__ = "pdf_resource_documents"

    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pdf_documents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
