from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
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


class _AnchorColumns:
    """Metne baglanan kayitlarin (alinti, kelime) ortak capa kolonlari (bkz. pdfkit/domain/anchoring.py)."""

    page: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # ilk parcanin sayfasi (sorgu icin)
    segments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    engine_fp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    anchor_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending_context")


class PdfAnnotationRow(_AnchorColumns, Base):
    __tablename__ = "pdf_annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(26), nullable=False, unique=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pdf_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label_key: Mapped[str] = mapped_column(String(24), nullable=False, default="general")
    color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    quote_exact: Mapped[str] = mapped_column(Text, nullable=False)
    quote_prefix: Mapped[str | None] = mapped_column(String(128), nullable=True)
    quote_suffix: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )
    legacy_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)


class PdfPageNoteRow(Base):
    __tablename__ = "pdf_page_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(26), nullable=False, unique=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pdf_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )
    legacy_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)


class PdfTermRow(_AnchorColumns, Base):
    __tablename__ = "pdf_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(26), nullable=False, unique=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pdf_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    word: Mapped[str] = mapped_column(String(200), nullable=False)
    translation: Mapped[str] = mapped_column(String(200), nullable=False)
    context_sentence: Mapped[str | None] = mapped_column(Text, nullable=True)
    mastery_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    legacy_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
