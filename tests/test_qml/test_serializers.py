from datetime import datetime

from models import Category, Highlight, PdfNote, Resource, ResourceStatus, Tag, Vocabulary
from pdfkit.api import Annotation, Document, PageNote, ResourceAnnotations, Term
from pdfkit.domain.annotations import STATUS_OK, Segment
from ui_qml.serializers import (
    serialize_highlight,
    serialize_paper_metadata,
    serialize_pdf_highlight,
    serialize_pool_pdf_highlight,
    serialize_pool_pdf_term,
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


def _document() -> Document:
    return Document(id=1, sha256="a" * 64, rel_path="store/aa/x.pdf", byte_size=1, page_count=3, has_text_layer=True,
                    pdf_title=None, pdf_author=None, doi=None, source="local", original_filename="x.pdf", imported_at=None)


def _annotation(**overrides) -> Annotation:
    defaults = dict(
        id=4, uid="U" * 26, document_id=1, label_key="method", color=None, comment="yorum", tags=[],
        quote_exact="alinti metni", quote_prefix=None, quote_suffix=None,
        segments=[Segment(2, 100, 112, "alinti metni", [[(1.0, 2.0)]])], engine_fp="fp", status=STATUS_OK,
        created_at=datetime(2026, 10, 1, 12, 0),
    )
    defaults.update(overrides)
    return Annotation(**defaults)


def test_serialize_resource_exposes_every_key_qml_relies_on():
    data = serialize_resource(_resource(), pdf_data=None, pdf_file_url="", pdf_state="")

    assert set(data) == _RESOURCE_KEYS


def test_serialize_resource_maps_fields_and_defaults_for_a_non_pdf_resource():
    resource = _resource(extra_metadata={"image": "https://x/i.png", "description": "Aciklama", "authors": ["Ada"],
                                         "year": 2020, "citation_count": 3, "openalex_id": "W1"})
    resource.category = Category(id=2, name="Makale", color_hex="#123456")
    resource.tags = [Tag(id=5, name="ai")]
    resource.vocabulary = [Vocabulary(id=1, word="kelime", translation="word", context_sentence=None)]
    resource.pdf_notes = [PdfNote(id=2, page=1, x=1.5, y=2.5, note_text="not")]
    resource.highlights = [Highlight(id=3, resource_id=7, content="web alintisi", color="#EAB308")]

    data = serialize_resource(resource, pdf_data=None, pdf_file_url="file:///a.pdf", pdf_state="ready")

    assert data["domain"] == "example.com" and data["categoryName"] == "Makale" and data["categoryColor"] == "#123456"
    assert data["thumbnailUrl"] == "https://x/i.png" and data["description"] == "Aciklama"
    assert data["tags"] == [{"id": 5, "name": "ai"}]
    assert data["vocabulary"] == [{"id": 1, "word": "kelime", "translation": "word", "context": ""}]
    assert data["pdfNotes"] == [{"id": 2, "page": 1, "x": 1.5, "y": 2.5, "text": "not"}]
    assert data["paper"]["authors"] == ["Ada"] and data["paper"]["openalexId"] == "W1" and data["paper"]["citationCount"] == 3
    assert [h["content"] for h in data["highlights"]] == ["web alintisi"]
    assert data["pdfFileUrl"] == "file:///a.pdf" and data["pdfState"] == "ready"
    assert data["status"] == "PLANNED" and data["readingMinutes"] == 4
    assert data["createdAt"] == data["createdAt"].strip() and data["createdAt"] != ""


def test_pdf_resources_take_highlights_notes_and_terms_from_pdfkit_and_ignore_orm_collections():
    resource = _resource()
    resource.highlights = [Highlight(id=9, resource_id=7, content="eski tablo", color="#EAB308")]  # yok sayilir
    pdf_data = ResourceAnnotations(
        document=_document(),
        highlights=[_annotation()],
        notes=[PageNote(id=2, uid="N" * 26, document_id=1, page=1, x=1.5, y=2.5, text="pdf notu")],
        terms=[Term(id=3, uid="T" * 26, document_id=1, word="tilki", translation="fox", context_sentence="Hizli tilki.",
                    mastery_level=0)],
    )

    data = serialize_resource(resource, pdf_data=pdf_data, pdf_file_url="file:///a.pdf", pdf_state="ready")

    assert [h["content"] for h in data["highlights"]] == ["alinti metni"]
    assert data["pdfNotes"] == [{"id": 2, "page": 1, "x": 1.5, "y": 2.5, "text": "pdf notu"}]
    assert data["vocabulary"] == [{"id": 3, "word": "tilki", "translation": "fox", "context": "Hizli tilki."}]


def test_serialize_resource_without_category_url_or_metadata():
    data = serialize_resource(_resource(url=None), pdf_data=None, pdf_file_url="", pdf_state="")

    assert data["url"] == "" and data["domain"] == ""
    assert data["categoryId"] == 0 and data["categoryName"] == "" and data["categoryColor"] == "#64748B"
    assert data["paper"] == serialize_paper_metadata({})


def test_serialize_highlight_defaults():
    plain = Highlight(id=1, resource_id=1, content="metin", color=None)

    item = serialize_highlight(plain)

    assert item["color"] == "#B45309" and item["page"] == -1 and item["startIndex"] == -1 and item["length"] == -1
    assert "boundsPolygons" not in item

    positioned = Highlight(id=2, resource_id=1, content="x", color="#EAB308", page_number=3, start_index=10, length=4,
                           comment="yorum")
    item = serialize_highlight(positioned)

    assert (item["page"], item["startIndex"], item["length"], item["comment"]) == (3, 10, 4, "yorum")


def test_pdf_highlight_summary_has_label_effective_color_and_no_geometry():
    item = serialize_pdf_highlight(_annotation())

    assert (item["content"], item["label"], item["color"], item["comment"]) == ("alinti metni", "Yöntem", "#06B6D4", "yorum")
    assert (item["page"], item["startIndex"], item["length"]) == (2, 100, 12)
    assert "boundsPolygons" not in item and "boundingRect" not in item


def test_pool_entries_carry_namespaced_keys_so_deletion_knows_the_source():
    class Entry:
        resource_id, resource_title = 7, "Makale"

    highlight_entry, term_entry = Entry(), Entry()
    highlight_entry.annotation = _annotation()
    term_entry.term = Term(id=3, uid="T" * 26, document_id=1, word="tilki", translation="fox", context_sentence=None,
                           mastery_level=0, created_at=datetime(2026, 10, 1))

    pool_highlight = serialize_pool_pdf_highlight(highlight_entry)
    pool_term = serialize_pool_pdf_term(term_entry)

    assert pool_highlight["key"] == "pdf:4" and pool_highlight["resource_title"] == "Makale" and pool_highlight["page"] == 2
    assert pool_term["key"] == "pdf:3" and pool_term["word"] == "tilki" and pool_term["context_sentence"] == ""
