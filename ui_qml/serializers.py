"""Model nesnelerini QML'in tukettigi duz sozluklere ceviren saf fonksiyonlar (Qt/PDF bagimsiz).

`QmlBridge._serialize_resource` yalnizca PDF durumuna bagli kisimlari (dosya URL'si, indirme
durumu, alinti geometrisi) hesaplar; geri kalan donusum burada test edilebilir parcalardadir.
"""
import html
from typing import TYPE_CHECKING

from core.constants.highlight_labels import label_for_color
from models import Highlight, Resource, Vocabulary
from pdfkit.api import (
    STATUS_ORPHANED,
    Annotation,
    ResourceAnnotations,
    color_for_label,
    column_name,
    effective_color,
    name_for_label,
    shorten_text,
)
from services.library_index import LibraryIndex
from services.paper_market_service import PaperResult
from utils.date_utils import format_local_datetime
from utils.url_utils import format_display_url

if TYPE_CHECKING:
    from pdfkit.api import PdfLibrary
    from ui_qml.pdf_files import PdfFileManager

DEFAULT_HIGHLIGHT_COLOR = "#B45309"
DEFAULT_CATEGORY_COLOR = "#64748B"


def serialize_highlight(highlight: Highlight) -> dict:
    """HTML makale alintisi (PDF belgelerinin alintilari pdfkit'ten gelir, bkz. `serialize_pdf_highlight`)."""
    return {
        "id": highlight.id,
        "content": highlight.content,
        "color": highlight.color or DEFAULT_HIGHLIGHT_COLOR,
        "label": label_for_color(highlight.color),
        "comment": highlight.comment or "",
        "page": highlight.page_number if highlight.page_number is not None else -1,
        "startIndex": highlight.start_index if highlight.start_index is not None else -1,
        "length": highlight.length if highlight.length is not None else -1,
    }


def serialize_pdf_highlight(annotation: Annotation) -> dict:
    """pdfkit alintisi, kaynak sozlugundeki (cekmece ozeti) alinti bicimiyle; geometri hesaplanmaz."""
    first = annotation.segments[0] if annotation.segments else None
    return {
        "id": annotation.id,
        "content": annotation.quote_exact,
        "color": effective_color(annotation.label_key, annotation.color),
        "label": name_for_label(annotation.label_key),
        "comment": annotation.comment or "",
        "page": first.page if first else -1,
        "startIndex": first.start if first else -1,
        "length": (first.end - first.start) if first else -1,
    }


def serialize_pool_pdf_highlight(entry) -> dict:
    """Bilgi Havuzu'ndaki pdfkit alintisi (`key` kaynagi belirtir: silme `pdf:<id>` ile yapilir)."""
    annotation = entry.annotation
    first = annotation.segments[0] if annotation.segments else None
    return {
        "key": f"pdf:{annotation.id}",
        "id": annotation.id,
        "resource_id": entry.resource_id,
        "resource_title": entry.resource_title or "İsimsiz",
        "content": annotation.quote_exact,
        "color": effective_color(annotation.label_key, annotation.color),
        "label": name_for_label(annotation.label_key),
        "comment": annotation.comment or "",
        "tags": list(annotation.tags),
        "page": first.page if first else -1,
        "created_at": format_local_datetime(annotation.created_at),
    }


def serialize_pool_pdf_term(entry) -> dict:
    term = entry.term
    return {
        "key": f"pdf:{term.id}",
        "id": term.id,
        "resource_id": entry.resource_id,
        "resource_title": entry.resource_title or "İsimsiz",
        "word": term.word,
        "translation": term.translation,
        "context_sentence": term.context_sentence or "",
        "created_at": format_local_datetime(term.created_at),
    }


def serialize_pool_highlight(highlight: Highlight) -> dict:
    """Bilgi Havuzu'ndaki alinti satiri (kaynak basligi ve olusturma zamani ile)."""
    return {
        "key": f"html:{highlight.id}",
        "id": highlight.id,
        "resource_id": highlight.resource_id,
        "resource_title": highlight.resource.title if highlight.resource else "İsimsiz",
        "content": highlight.content,
        "color": highlight.color or DEFAULT_HIGHLIGHT_COLOR,
        "label": label_for_color(highlight.color),
        "comment": highlight.comment or "",
        "tags": [],  # HTML makale alintilarinda serbest etiket yok (yalniz PDF alintilarinda)
        "page": highlight.page_number if highlight.page_number is not None else -1,
        "created_at": format_local_datetime(highlight.created_at),
    }


def serialize_pool_vocabulary(entry: Vocabulary) -> dict:
    """Bilgi Havuzu'ndaki kelime satiri (kaynak basligi ve olusturma zamani ile)."""
    return {
        "key": f"html:{entry.id}",
        "id": entry.id,
        "resource_id": entry.resource_id,
        "resource_title": entry.resource.title if entry.resource else "İsimsiz",
        "word": entry.word,
        "translation": entry.translation,
        "context_sentence": entry.context_sentence or "",
        "created_at": format_local_datetime(entry.created_at),
    }


def serialize_paper_metadata(meta: dict) -> dict:
    return {
        "authors": meta.get("authors") or [],
        "year": meta.get("year"),
        "venue": meta.get("venue") or "",
        "doi": meta.get("doi") or "",
        "openalexId": meta.get("openalex_id") or "",
        "citationCount": meta.get("citation_count") or 0,
    }


def _category_fields(resource: Resource) -> dict:
    category = resource.category
    return {
        "categoryId": resource.category_id or 0,
        "categoryName": category.name if category else "",
        "categoryColor": category.color_hex if category and category.color_hex else DEFAULT_CATEGORY_COLOR,
    }


def _display_fields(resource: Resource) -> dict:
    meta = resource.extra_metadata or {}
    return {
        "domain": format_display_url(resource.url) if resource.url else "",
        "thumbnailUrl": str(meta.get("image") or meta.get("thumbnail") or ""),
        "description": str(meta.get("description") or ""),
        "paper": serialize_paper_metadata(meta),
    }


def _core_fields(resource: Resource) -> dict:
    return {
        "id": resource.id,
        "title": resource.title or "",
        "url": resource.url or "",
        "status": resource.status.value if hasattr(resource.status, "value") else str(resource.status),
        "priority": resource.priority,
        "isPinned": bool(resource.is_pinned),
        "isFavorite": bool(resource.is_favorite),
        "content": resource.content or "",
        "fullText": resource.full_text or "",
        "readingMinutes": resource.reading_minutes or 0,
        "createdAt": format_local_datetime(resource.created_at),
    }


def _annotation_fields(resource: Resource, pdf_data: ResourceAnnotations | None) -> dict:
    """Cekmecedeki alintilar: PDF belgesi olan kaynaklarda pdfkit'ten, digerlerinde (HTML makale) eski `highlights`
    tablosundan. Geometri burada hesaplanmaz (PDF okuyucu `bridge.pdf` modellerini kullanir)."""
    if pdf_data is not None:
        return {"highlights": [serialize_pdf_highlight(a) for a in pdf_data.highlights]}
    return {"highlights": [serialize_highlight(h) for h in (resource.highlights or [])]}


def _relation_fields(resource: Resource) -> dict:
    return {"tags": [{"id": tag.id, "name": tag.name} for tag in resource.tags]}


def serialize_resource(
    resource: Resource, *, pdf_data: ResourceAnnotations | None, pdf_file_url: str, pdf_state: str
) -> dict:
    return {
        **_core_fields(resource),
        **_relation_fields(resource),
        **_annotation_fields(resource, pdf_data),
        "pdfFileUrl": pdf_file_url,
        "pdfState": pdf_state,
        **_category_fields(resource),
        **_display_fields(resource),
    }


class ResourceSerializer:
    """Kaynagi QML sozlugune cevirir; PDF'e bagli kisimlari (dosya URL'si, indirme durumu) `PdfFileManager`'dan,
    PDF belgesi olan kaynaklarin alinti/not/kelimelerini pdfkit'ten alir (geometri hesaplanmaz), gerisi saf
    fonksiyonlardir."""

    def __init__(self, pdf_files: "PdfFileManager", pdf_library: "PdfLibrary") -> None:
        self._pdf_files = pdf_files
        self._pdf_library = pdf_library

    def serialize(self, resource: Resource) -> dict:
        pdf_file_url = self._pdf_files.pdf_file_url(resource)
        return serialize_resource(
            resource,
            pdf_data=self._pdf_library.annotations_of(resource.id),
            pdf_file_url=pdf_file_url or "",
            pdf_state=self._pdf_files.state(resource, pdf_file_url),
        )


def serialize_paper(paper: PaperResult) -> dict:
    """OpenAlex sonucunu (Market/Kaynakca/oneri) QML sozlugune cevirir; `libraryResourceId` sonradan
    `annotate_library` ile yazilir (0 = kutuphanede yok)."""
    return {
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.year,
        "citationCount": paper.citation_count,
        "url": paper.url or "",
        "abstract": paper.abstract or "",
        "venue": paper.venue or "",
        "doi": paper.doi or "",
        "openalexId": paper.openalex_id or "",
        "authorIds": paper.author_ids,
        "isOpenAccess": paper.is_open_access,
        "hasPdf": paper.has_pdf,
        "libraryResourceId": 0,
    }


def annotate_library(items: list[dict], index: LibraryIndex) -> bool:
    """Sonuclara kutuphanedeki karsiliginin id'sini (`libraryResourceId`, 0 = yok) yazar;
    herhangi bir deger degistiyse True doner."""
    changed = False
    for item in items:
        match = index.find(item.get("doi"), item.get("openalexId")) or 0
        if item.get("libraryResourceId") != match:
            item["libraryResourceId"] = match
            changed = True
    return changed


def snippet_html(snippet) -> str:
    """Ozet parcasi, eslesmeleri `<b>` ile vurgulanmis QML `Text.StyledText` metni (metin kacirilir)."""
    parts, cursor = [], 0
    for start, end in snippet.spans:
        parts.append(html.escape(snippet.text[cursor:start]))
        parts.append(f"<b>{html.escape(snippet.text[start:end])}</b>")
        cursor = end
    parts.append(html.escape(snippet.text[cursor:]))
    return "".join(parts)


MAX_HITS_SHOWN_PER_RESOURCE = 5


def serialize_search_group(group) -> dict:
    """Tam metin aramasi sonucu: kaynak + (en cok 5) sayfa eslesmesi; `more` gosterilmeyen sayfa sayisi."""
    shown = group.hits[:MAX_HITS_SHOWN_PER_RESOURCE]
    return {
        "resourceId": group.resource_id,
        "title": group.title or "İsimsiz",
        "hits": [{"page": hit.page, "html": snippet_html(hit.snippet)} for hit in shown],
        "more": group.total - len(shown),
    }


def serialize_matrix(matrix) -> dict:
    """Literatur matrisi (QML icin): sutunlar [{key, name, color, count}], satirlar [{resourceId, title, citekey, year,
    count, cells}]; `cells` sutunlarla ayni sirada alinti listeleri ([{id, uid, page (0 tabanli), pageLabel, text,
    comment, orphaned, tags}]). Uzun alinti/yorum kisaltilir (tam metin okuyucuda)."""
    columns = []
    for key in matrix.columns:
        count = sum(len(row.cells.get(key, ())) for row in matrix.rows)
        columns.append({"key": key, "name": column_name(key), "color": color_for_label(key) or "", "count": count})
    rows = []
    for row in matrix.rows:
        cells = []
        for key in matrix.columns:
            cells.append(
                [
                    {
                        "id": a.id,
                        "uid": a.uid,
                        "page": a.page if a.page is not None else -1,
                        "pageLabel": f"s. {a.page + 1}" if a.page is not None and a.status != STATUS_ORPHANED else "",
                        "text": shorten_text(" ".join(a.quote_exact.split())),
                        "comment": shorten_text(" ".join((a.comment or "").split())),
                        "orphaned": a.status == STATUS_ORPHANED or a.page is None,
                        "tags": list(a.tags),
                    }
                    for a in row.cells.get(key, ())
                ]
            )
        rows.append(
            {
                "resourceId": row.resource_id or 0,
                "title": row.title or "İsimsiz",
                "citekey": row.citekey or "",
                "year": row.year or 0,
                "count": row.annotation_count,
                "cells": cells,
            }
        )
    return {"columns": columns, "rows": rows, "rowCount": len(rows), "annotationCount": matrix.annotation_count}
