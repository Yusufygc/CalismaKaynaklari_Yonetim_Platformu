"""Model nesnelerini QML'in tukettigi duz sozluklere ceviren saf fonksiyonlar (Qt/PDF bagimsiz).

`QmlBridge._serialize_resource` yalnizca PDF durumuna bagli kisimlari (dosya URL'si, indirme
durumu, alinti geometrisi) hesaplar; geri kalan donusum burada test edilebilir parcalardadir.
"""
from typing import TYPE_CHECKING

from core.constants.highlight_labels import label_for_color
from models import Highlight, PdfNote, Resource, Vocabulary
from services.library_index import LibraryIndex
from services.paper_market_service import PaperResult
from utils.date_utils import format_local_datetime
from utils.url_utils import format_display_url

if TYPE_CHECKING:
    from ui_qml.pdf_files import PdfFileManager

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


def serialize_pool_highlight(highlight: Highlight) -> dict:
    """Bilgi Havuzu'ndaki alinti satiri (kaynak basligi ve olusturma zamani ile)."""
    return {
        "id": highlight.id,
        "resource_id": highlight.resource_id,
        "resource_title": highlight.resource.title if highlight.resource else "İsimsiz",
        "content": highlight.content,
        "color": highlight.color or DEFAULT_HIGHLIGHT_COLOR,
        "label": label_for_color(highlight.color),
        "comment": highlight.comment or "",
        "page": highlight.page_number if highlight.page_number is not None else -1,
        "created_at": format_local_datetime(highlight.created_at),
    }


def serialize_pool_vocabulary(entry: Vocabulary) -> dict:
    """Bilgi Havuzu'ndaki kelime satiri (kaynak basligi ve olusturma zamani ile)."""
    return {
        "id": entry.id,
        "resource_id": entry.resource_id,
        "resource_title": entry.resource.title if entry.resource else "İsimsiz",
        "word": entry.word,
        "translation": entry.translation,
        "context_sentence": entry.context_sentence or "",
        "created_at": format_local_datetime(entry.created_at),
    }


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


class ResourceSerializer:
    """Kaynagi QML sozlugune cevirir; yalnizca yerel PDF'e bagli kisimlari (dosya URL'si, indirme
    durumu, alinti geometrisi) `PdfFileManager`'dan alir, gerisi saf fonksiyonlardir."""

    def __init__(self, pdf_files: "PdfFileManager") -> None:
        self._pdf_files = pdf_files

    def serialize(self, resource: Resource) -> dict:
        pdf_file_url = self._pdf_files.pdf_file_url(resource)
        return serialize_resource(
            resource,
            highlights=self._highlights(resource, pdf_file_url),
            pdf_file_url=pdf_file_url or "",
            pdf_state=self._pdf_files.state(resource, pdf_file_url),
        )

    def _highlights(self, resource: Resource, pdf_file_url: str | None) -> list[dict]:
        """Alintilar; yerel PDF ise kalici alintilarin yeniden cizilebilmesi icin geometri
        (poligon + bounding rect) onceden hesaplanir (QML'den QPdfSelection donen metotlar
        cagrilamiyor, bkz. ReaderBridge.addPdfHighlight)."""
        pdf_doc = self._pdf_files.load_document(pdf_file_url) if pdf_file_url else None
        items = []
        for highlight in resource.highlights or []:
            geometry = None
            if pdf_doc is not None and has_pdf_position(highlight):
                geometry = self._pdf_files.highlight_geometry(
                    pdf_doc, highlight.page_number, highlight.start_index, highlight.length
                )
            items.append(serialize_highlight(highlight, geometry))
        return items


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
