from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PdfInspection:
    """Bir PDF'in dosya duzeyi ozeti (PDFium'dan)."""

    page_count: int
    has_text_layer: bool
    title: str | None
    author: str | None
    doi: str | None


@dataclass(frozen=True)
class StoredFile:
    """Dosya deposuna alinmis PDF."""

    sha256: str
    rel_path: str  # depo kokune gore, '/' ayiracli
    byte_size: int
    created: bool  # False: ayni icerik zaten depoda vardi


@dataclass(frozen=True)
class PreparedPdf:
    """Arka planda hazirlanan PDF: depoya alinmis dosya + inceleme sonucu (veritabanina henuz yazilmadi)."""

    stored: StoredFile
    inspection: PdfInspection
    original_filename: str | None


@dataclass(frozen=True)
class Document:
    id: int
    sha256: str
    rel_path: str
    byte_size: int
    page_count: int
    has_text_layer: bool
    pdf_title: str | None
    pdf_author: str | None
    doi: str | None
    source: str  # "local" | "web"
    original_filename: str | None
    imported_at: datetime | None


@dataclass(frozen=True)
class SourceInfo:
    """Belgenin bagli oldugu kaynagin (Resource) kunyesi: citekey ve vault notu icin. Uygulama tarafi doldurur."""

    title: str
    authors: tuple[str, ...] = ()
    year: int | None = None
    doi: str | None = None
    status: str = ""  # kullaniciya gorunen okuma durumu ("Gelen Kutusu", "Tamamlandi", ...)
    url: str | None = None  # web kaynagi adresi (yerel dosya degil)
