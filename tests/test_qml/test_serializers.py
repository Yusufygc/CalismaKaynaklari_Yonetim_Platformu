from datetime import datetime

from models import Category, Highlight, PdfNote, Resource, ResourceStatus, Tag, Vocabulary
from ui_qml.serializers import (
    has_pdf_position,
    serialize_highlight,
    serialize_paper_metadata,
    serialize_resource,
)

_RESOURCE_KEYS = {
    "id", "title", "url", "domain", "categoryId", "categoryName", "categoryColor", "status", "priority",
    "isPinned", "isFavorite", "content", "fullText", "thumbnailUrl", "description", "readingMinutes", "tags",
    "highlights", "vocabulary", "pdfNotes", "pdfFileUrl", "pdfState", "paper", "createdAt",
}


def _resource(**overrides) -> Resource:
    defaults = dict(id=7, title="Baslik", url="https://www.example.com/a", status=ResourceStatus.PLANNED, priority=2,
                    is_pinned=False, is_favorite=False, reading_minutes=4, created_at=datetime(2026, 9, 29, 21, 58))
    defaults.update(overrides)
    return Resource(**defaults)


def test_serialize_resource_exposes_every_key_qml_relies_on():
    data = serialize_resource(_resource(), highlights=[], pdf_file_url="", pdf_state="")

    assert set(data) == _RESOURCE_KEYS


def test_serialize_resource_maps_fields_and_defaults():
    resource = _resource(extra_metadata={"image": "https://x/i.png", "description": "Aciklama", "authors": ["Ada"],
                                         "year": 2020, "citation_count": 3, "openalex_id": "W1"})
    resource.category = Category(id=2, name="Makale", color_hex="#123456")
    resource.tags = [Tag(id=5, name="ai")]
    resource.vocabulary = [Vocabulary(id=1, word="kelime", translation="word", context_sentence=None)]
    resource.pdf_notes = [PdfNote(id=2, page=1, x=1.5, y=2.5, note_text="not")]

    data = serialize_resource(resource, highlights=[{"id": 1}], pdf_file_url="file:///a.pdf", pdf_state="ready")

    assert data["domain"] == "example.com" and data["categoryName"] == "Makale" and data["categoryColor"] == "#123456"
    assert data["thumbnailUrl"] == "https://x/i.png" and data["description"] == "Aciklama"
    assert data["tags"] == [{"id": 5, "name": "ai"}]
    assert data["vocabulary"] == [{"id": 1, "word": "kelime", "translation": "word", "context": ""}]
    assert data["pdfNotes"] == [{"id": 2, "page": 1, "x": 1.5, "y": 2.5, "text": "not"}]
    assert data["paper"]["authors"] == ["Ada"] and data["paper"]["openalexId"] == "W1" and data["paper"]["citationCount"] == 3
    assert data["highlights"] == [{"id": 1}] and data["pdfFileUrl"] == "file:///a.pdf" and data["pdfState"] == "ready"
    assert data["status"] == "PLANNED" and data["readingMinutes"] == 4
    assert data["createdAt"] == data["createdAt"].strip() and data["createdAt"] != ""


def test_serialize_resource_without_category_url_or_metadata():
    data = serialize_resource(_resource(url=None), highlights=[], pdf_file_url="", pdf_state="")

    assert data["url"] == "" and data["domain"] == ""
    assert data["categoryId"] == 0 and data["categoryName"] == "" and data["categoryColor"] == "#64748B"
    assert data["paper"] == serialize_paper_metadata({})


def test_serialize_highlight_defaults_and_geometry():
    plain = Highlight(id=1, resource_id=1, content="metin", color=None)

    item = serialize_highlight(plain)

    assert item["color"] == "#B45309" and item["page"] == -1 and item["startIndex"] == -1 and item["length"] == -1
    assert "boundsPolygons" not in item

    positioned = Highlight(id=2, resource_id=1, content="x", color="#EAB308", page_number=3, start_index=10, length=4,
                           comment="yorum")
    item = serialize_highlight(positioned, geometry=([[[0, 0]]], [1, 2, 3, 4]))

    assert (item["page"], item["startIndex"], item["length"], item["comment"]) == (3, 10, 4, "yorum")
    assert item["boundsPolygons"] == [[[0, 0]]] and item["boundingRect"] == [1, 2, 3, 4]


def test_has_pdf_position_requires_page_index_and_positive_length():
    assert has_pdf_position(Highlight(page_number=0, start_index=0, length=5))
    assert not has_pdf_position(Highlight(page_number=0, start_index=0, length=0))
    assert not has_pdf_position(Highlight(page_number=None, start_index=0, length=5))
    assert not has_pdf_position(Highlight(page_number=0, start_index=None, length=5))
