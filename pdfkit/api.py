"""pdfkit'in dis dunyaya acik tek yuzeyi. Uygulamanin geri kalani paketin icine dogrudan erismez."""
from pdfkit.app.ports import LegacyPdf, ResourceCatalogPort
from pdfkit.domain.annotations import Annotation, PageNote, Term
from pdfkit.domain.errors import DownloadError, NotAPdfError, PdfkitError, TooLargeError, VaultUnavailableError
from pdfkit.domain.labels import effective_color, name_for_label
from pdfkit.domain.models import Document, PdfInspection, SourceInfo
from pdfkit.infra.text import extract_page_texts
from pdfkit.ui.bridge import PdfBridge
from pdfkit.ui.library import ImportOutcome, PdfLibrary, ResourceAnnotations
from pdfkit.ui.vault import SyncReport, VaultSync

__all__ = [
    "Annotation",
    "Document",
    "DownloadError",
    "ImportOutcome",
    "LegacyPdf",
    "NotAPdfError",
    "PageNote",
    "PdfBridge",
    "PdfInspection",
    "PdfLibrary",
    "PdfkitError",
    "ResourceAnnotations",
    "ResourceCatalogPort",
    "SourceInfo",
    "SyncReport",
    "Term",
    "TooLargeError",
    "VaultSync",
    "VaultUnavailableError",
    "effective_color",
    "extract_page_texts",
    "name_for_label",
]
