"""pdfkit'in dis dunyaya acik tek yuzeyi. Uygulamanin geri kalani paketin icine dogrudan erismez."""
from pdfkit.app.ports import LegacyPdf, ResourceCatalogPort
from pdfkit.domain.annotations import STATUS_ORPHANED, Annotation, PageNote, Term
from pdfkit.domain.deeplink import OpenLink, build_open_link, parse_open_link
from pdfkit.domain.errors import (
    DownloadError,
    InvalidLinkError,
    NotAPdfError,
    PdfkitError,
    TooLargeError,
    VaultUnavailableError,
)
from pdfkit.domain.labels import color_for_label, effective_color, name_for_label
from pdfkit.domain.models import Document, PdfInspection, SourceInfo
from pdfkit.domain.vault_note import obsidian_tag
from pdfkit.infra.outline import read_outline
from pdfkit.infra.text import extract_page_texts
from pdfkit.ui.bridge import PdfBridge
from pdfkit.domain.search import SearchHit, Snippet
from pdfkit.domain.synthesis import (
    DEFAULT_VAULT_CELL_LIMIT,
    Matrix,
    MatrixFilter,
    MatrixOptions,
    MatrixRow,
    column_keys,
    column_name,
    document_ids_matching,
    make_matrix,
    ordered_columns,
    render_markdown,
    tag_counts,
    with_provisional_citekeys,
)
from pdfkit.domain.synthesis import shorten as shorten_text
from pdfkit.ui.indexer import TextIndexer
from pdfkit.ui.library import ImportOutcome, PdfLibrary, ResourceAnnotations
from pdfkit.ui.vault import SyncReport, VaultSync

__all__ = [
    "Annotation",
    "Matrix",
    "MatrixFilter",
    "DEFAULT_VAULT_CELL_LIMIT",
    "MatrixOptions",
    "MatrixRow",
    "STATUS_ORPHANED",
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
    "color_for_label",
    "column_keys",
    "column_name",
    "document_ids_matching",
    "effective_color",
    "extract_page_texts",
    "make_matrix",
    "ordered_columns",
    "name_for_label",
    "obsidian_tag",
    "parse_open_link",
    "read_outline",
    "render_markdown",
    "shorten_text",
    "tag_counts",
    "with_provisional_citekeys",
]
