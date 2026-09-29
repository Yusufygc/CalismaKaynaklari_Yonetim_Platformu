"""Model nesnelerini QML'in tukettigi duz sozluklere ceviren saf fonksiyonlar (Qt/PDF bagimsiz).

`QmlBridge._serialize_resource` yalnizca PDF durumuna bagli kisimlari (dosya URL'si, indirme
durumu, alinti geometrisi) hesaplar; geri kalan donusum burada test edilebilir parcalardadir.
"""
from core.constants.highlight_labels import label_for_color
from models import Highlight, PdfNote, Resource, Vocabulary
from utils.date_utils import format_local_datetime
from utils.url_utils import format_display_url

DEFAULT_HIGHLIGHT_COLOR = "#B45309"
DEFAULT_CATEGORY_COLOR = "#64748B"


def serialize_highlight(highlight: Highlight, geometry: tuple[list, list] | None = None) -> dict:
    """`geometry`: yerel PDF'te alintinin (poligonlar, sinirlayici dikdortgen) hesaplanmis konumu."""
    item = {
        "id": highlight.id,
        "content": highlight.content,
        "color": highlight.color or DEFAULT_HIGHLIGHT_COLOR,
        "label": label_for_color(highlight.color),
        "comment": highlight.comment or "",
        "page": highlight.page_number if highlight.page_number is not None else -1,
        "startIndex": highlight.start_index if highlight.start_index is not None else -1,
        "length": highlight.length if highlight.length is not None else -1,
    }
    if geometry is not None:
        item["boundsPolygons"], item["boundingRect"] = geometry
    return item


def has_pdf_position(highlight: Highlight) -> bool:
    """Alintinin sayfa + karakter konumu kayitli mi (geometri hesaplanabilir mi)?"""
    return highlight.page_number is not None and highlight.start_index is not None and bool(highlight.length)


def serialize_vocabulary_entry(entry: Vocabulary) -> dict:
    return {
        "id": entry.id,
        "word": entry.word,
        "translation": entry.translation,
        "context": entry.context_sentence or "",
    }


def serialize_pdf_note(note: PdfNote) -> dict:
    return {"id": note.id, "page": note.page, "x": note.x, "y": note.y, "text": note.note_text}


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


def serialize_resource(resource: Resource, *, highlights: list[dict], pdf_file_url: str, pdf_state: str) -> dict:
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
        "tags": [{"id": tag.id, "name": tag.name} for tag in resource.tags],
        "highlights": highlights,
        "vocabulary": [serialize_vocabulary_entry(v) for v in (resource.vocabulary or [])],
        "pdfNotes": [serialize_pdf_note(n) for n in (resource.pdf_notes or [])],
        "pdfFileUrl": pdf_file_url,
        "pdfState": pdf_state,
        "createdAt": format_local_datetime(resource.created_at),
        **_category_fields(resource),
        **_display_fields(resource),
    }
