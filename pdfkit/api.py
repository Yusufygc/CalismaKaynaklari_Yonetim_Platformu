"""pdfkit'in dis dunyaya acik tek yuzeyi. Uygulamanin geri kalani paketin icine dogrudan erismez."""
from pdfkit.app.ports import LegacyPdf, ResourceCatalogPort
from pdfkit.domain.annotations import Annotation, PageNote, Term
from pdfkit.domain.deeplink import OpenLink, build_open_link, parse_open_link
from pdfkit.domain.errors import (
    DownloadError,
    InvalidLinkError,
    NotAPdfError,
    PdfkitError,
    TooLargeError,
    VaultUnavailableError,
)
from pdfkit.domain.labels import effective_color, name_for_label
from pdfkit.domain.models import Document, PdfInspection, SourceInfo
from pdfkit.domain.vault_note import obsidian_tag
from pdfkit.infra.text import extract_page_texts
from pdfkit.ui.bridge import PdfBridge
from pdfkit.domain.search import SearchHit, Snippet
from pdfkit.ui.indexer import TextIndexer
from pdfkit.ui.library import ImportOutcome, PdfLibrary, ResourceAnnotations
from pdfkit.ui.vault import SyncReport, VaultSync

__all__ = [
    "Annotation",
    "Document",
    "DownloadError",
    "ImportOutcome",
    "InvalidLinkError",
    "LegacyPdf",
    "NotAPdfError",
    "OpenLink",
    "PageNote",
    "PdfBridge",
    "PdfInspection",
    "PdfLibrary",
    "PdfkitError",
    "ResourceAnnotations",
    "ResourceCatalogPort",
    "SearchHit",
    "Snippet",
    "SourceInfo",
    "SyncReport",
    "Term",
    "TextIndexer",
    "TooLargeError",
    "VaultSync",
    "VaultUnavailableError",
    "build_open_link",
    "effective_color",
    "extract_page_texts",
    "name_for_label",
    "obsidian_tag",
    "parse_open_link",
]
