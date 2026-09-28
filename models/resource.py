import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Column,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ResourceStatus(enum.Enum):
    INBOX = "INBOX"
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

    @property
    def label(self) -> str:
        from core.constants.strings import AppStrings

        labels = {
            ResourceStatus.INBOX: AppStrings.FORM_STATUS_INBOX,
            ResourceStatus.PLANNED: AppStrings.FORM_STATUS_PLANNED,
            ResourceStatus.IN_PROGRESS: AppStrings.FORM_STATUS_IN_PROGRESS,
            ResourceStatus.COMPLETED: AppStrings.FORM_STATUS_COMPLETED,
        }
        return labels.get(self, self.value)


def status_label(status: ResourceStatus | str) -> str:
    if isinstance(status, ResourceStatus):
        return status.label
    try:
        return ResourceStatus(status).label
    except ValueError:
        return str(status)


# N:N iliski tablosu
resource_tags_link = Table(
    "resource_tags_link",
    Base.metadata,
    Column("resource_id", Integer, ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True, index=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[ResourceStatus] = mapped_column(
        Enum(ResourceStatus), nullable=False, default=ResourceStatus.PLANNED, index=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )

    category: Mapped["Category | None"] = relationship(  # type: ignore[name-defined]
        "Category", back_populates="resources"
    )
    tags: Mapped[list["Tag"]] = relationship(  # type: ignore[name-defined]
        "Tag", secondary="resource_tags_link", back_populates="resources"
    )
    highlights: Mapped[list["Highlight"]] = relationship(  # type: ignore[name-defined]
        "Highlight", back_populates="resource", cascade="all, delete-orphan"
    )
    vocabulary: Mapped[list["Vocabulary"]] = relationship(  # type: ignore[name-defined]
        "Vocabulary", back_populates="resource", cascade="all, delete-orphan"
    )
    pdf_notes: Mapped[list["PdfNote"]] = relationship(  # type: ignore[name-defined]
        "PdfNote", back_populates="resource", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Resource id={self.id} title={self.title!r} status={self.status.value}>"


class Highlight(Base):
    __tablename__ = "highlights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Native PDF highlight'ları icin (2026-09-29): piksel/geometri degil,
    # karakter-index bazli konum -- QPdfDocument.getSelectionAtIndex(page,
    # start_index, length) ile zoom/scroll'dan bagimsiz yeniden cizilir.
    # HTML-makale highlight'larinda hep null kalir.
    start_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    resource: Mapped["Resource"] = relationship("Resource", back_populates="highlights")

    def __repr__(self) -> str:
        return f"<Highlight id={self.id} resource_id={self.resource_id}>"


class Vocabulary(Base):
    __tablename__ = "vocabulary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    word: Mapped[str] = mapped_column(String(200), nullable=False)
    translation: Mapped[str] = mapped_column(String(200), nullable=False)
    context_sentence: Mapped[str | None] = mapped_column(Text, nullable=True)
    mastery_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    resource: Mapped["Resource"] = relationship("Resource", back_populates="vocabulary")

    def __repr__(self) -> str:
        return f"<Vocabulary id={self.id} word={self.word!r}>"


class PdfNote(Base):
    """Native PDF okuyucuda bir noktaya (satir/paragraf) birakilan margin not.

    Highlight'tan farkli: metin araligi degil tek bir nokta (page-point
    uzayinda, cozunurlukten bagimsiz) referans alir.
    """

    __tablename__ = "pdf_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    resource: Mapped["Resource"] = relationship("Resource", back_populates="pdf_notes")

    def __repr__(self) -> str:
        return f"<PdfNote id={self.id} resource_id={self.resource_id} page={self.page}>"
