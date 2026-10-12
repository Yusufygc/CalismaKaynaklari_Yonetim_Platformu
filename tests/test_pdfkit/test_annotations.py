import pytest

from pdfkit.domain.annotations import STATUS_OK, STATUS_ORPHANED, STATUS_PENDING, STATUS_UNANCHORED, Segment
from pdfkit.domain.anchoring import Resolution
from pdfkit.domain.errors import InvalidAnnotationError, NotFoundError


def _segment(text="alinti metni", page=2, start=10, polygons=None):
    return Segment(page, start, start + len(text), text, polygons)


def test_create_highlight_stores_anchor_label_tags_and_stable_uid(annotations, resource_with_document):
    _resource, document, _path = resource_with_document
    polygons = [[(1.0, 2.0), (3.0, 2.0), (3.0, 4.0), (1.0, 4.0)]]

    created = annotations.create_highlight(
        document.id, "  alinti metni ", [_segment(polygons=polygons)], "finding",
        color="#22C55E", comment="  onemli  ", tags=["#Derin-Ogrenme", "derin-ogrenme", " yontem "],
        prefix="onceki ", suffix=" sonraki", engine_fp="qtpdf-6.11.2",
    )

    loaded = annotations.get_highlight(created.id)
    assert len(created.uid) == 26 and loaded.uid == created.uid
    assert loaded.quote_exact == "alinti metni" and loaded.comment == "onemli"
    assert loaded.tags == ["derin-ogrenme", "yontem"]  # '#' atilir, kucuk harf, tekrar yok
    assert loaded.status == STATUS_OK and loaded.page == 2 and loaded.engine_fp == "qtpdf-6.11.2"
    assert loaded.segments[0].polygons == polygons  # geometri JSON'dan aynen geri gelir


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"quote_exact": "   "}, "bos"),
        ({"segments": []}, "parca"),
        ({"label_key": "uydurma"}, "etiket"),
    ],
)
def test_invalid_highlights_are_rejected(annotations, resource_with_document, kwargs, message):
    _r, document, _p = resource_with_document
    args = {"quote_exact": "metin", "segments": [_segment()], "label_key": "general", **kwargs}

    with pytest.raises(InvalidAnnotationError, match=message):
        annotations.create_highlight(document.id, args["quote_exact"], args["segments"], args["label_key"])


def test_highlight_for_missing_document_is_rejected(annotations):
    with pytest.raises(NotFoundError):
        annotations.create_highlight(999, "metin", [_segment()])


def test_lone_surrogates_are_sanitized_before_hitting_sqlite(annotations, resource_with_document):
    _r, document, _p = resource_with_document

    created = annotations.create_highlight(document.id, "bozuk font " + chr(0xD835) + " sembolu", [_segment()])

    assert chr(0xD835) not in created.quote_exact and len(created.quote_exact) == len("bozuk font ? sembolu")


def test_label_comment_and_tag_updates_persist(annotations, resource_with_document):
    _r, document, _p = resource_with_document
    created = annotations.create_highlight(document.id, "metin parcasi", [_segment("metin parcasi")])

    annotations.set_label(created.id, "method", "#06B6D4")
    annotations.set_comment(created.id, "yontem bolumu")
    annotations.set_tags(created.id, ["A", "b"])

    loaded = annotations.get_highlight(created.id)
    assert (loaded.label_key, loaded.color, loaded.comment, loaded.tags) == ("method", "#06B6D4", "yontem bolumu", ["a", "b"])
    annotations.set_comment(created.id, "   ")
    assert annotations.get_highlight(created.id).comment is None


def test_delete_and_bulk_delete(annotations, resource_with_document):
    _r, document, _p = resource_with_document
    ids = [annotations.create_highlight(document.id, f"metin {i} parca", [_segment(f"metin {i} parca")]).id for i in range(3)]

    annotations.delete_highlight(ids[0])
    assert annotations.delete_highlights([ids[1], ids[2], 12345]) == 2

    assert annotations.list_highlights(document.id) == []
    with pytest.raises(NotFoundError):
        annotations.delete_highlight(ids[0])


def test_highlights_are_listed_in_page_order(annotations, resource_with_document):
    _r, document, _p = resource_with_document
    for page in (5, 1, 3):
        annotations.create_highlight(document.id, f"sayfa {page} metni", [_segment(f"sayfa {page} metni", page=page)])

    assert [a.page for a in annotations.list_highlights(document.id)] == [1, 3, 5]


def test_apply_resolution_updates_anchor_and_orphaning_keeps_segments(annotations, resource_with_document):
    _r, document, _p = resource_with_document
    created = annotations.create_highlight(
        document.id, "alinti metni", [_segment()], status=STATUS_PENDING
    )
    moved = Resolution(STATUS_OK, [_segment(start=40)], "context", True, prefix="onceki", suffix="sonraki")

    after = annotations.apply_resolution(created.id, moved, "qtpdf-9")
    assert (after.status, after.segments[0].start, after.quote_prefix, after.quote_suffix, after.engine_fp) == (
        STATUS_OK, 40, "onceki", "sonraki", "qtpdf-9",
    )

    orphan = annotations.apply_resolution(created.id, Resolution(STATUS_ORPHANED, [], None, False), "qtpdf-9")
    assert orphan.status == STATUS_ORPHANED and orphan.segments[0].start == 40


def test_relink_binds_an_orphaned_highlight_to_a_new_selection(annotations, resource_with_document):
    _r, document, _p = resource_with_document
    created = annotations.create_highlight(document.id, "eski metin", [_segment("eski metin")], status=STATUS_ORPHANED)

    relinked = annotations.relink(created.id, [_segment("yeni metin", page=7, start=3)], "yeni metin", "on", "son", "qtpdf-9")

    assert (relinked.status, relinked.quote_exact, relinked.page) == (STATUS_OK, "yeni metin", 7)
    with pytest.raises(InvalidAnnotationError):
        annotations.relink(created.id, [], "x", None, None, None)


def test_page_notes_crud_and_validation(annotations, resource_with_document):
    _r, document, _p = resource_with_document

    note = annotations.create_note(document.id, 4, 12.5, 30.25, "  Bunu tekrar oku ")
    annotations.update_note(note.id, "Guncel not")

    (loaded,) = annotations.list_notes(document.id)
    assert (loaded.page, loaded.x, loaded.y, loaded.text, len(loaded.uid)) == (4, 12.5, 30.25, "Guncel not", 26)
    annotations.delete_note(note.id)
    assert annotations.list_notes(document.id) == []
    with pytest.raises(InvalidAnnotationError):
        annotations.create_note(document.id, -1, 0, 0, "x")
    with pytest.raises(InvalidAnnotationError):
        annotations.create_note(document.id, 0, 0, 0, "   ")


def test_terms_with_and_without_anchor(annotations, resource_with_document):
    _r, document, _p = resource_with_document

    anchored = annotations.create_term(document.id, " tilki ", " fox ", " Hizli kahverengi tilki. ", [_segment("tilki")])
    loose = annotations.create_term(document.id, "kopek", "dog")

    terms = {t.word: t for t in annotations.list_terms(document.id)}
    assert terms["tilki"].status == STATUS_OK and terms["tilki"].translation == "fox"
    assert terms["tilki"].context_sentence == "Hizli kahverengi tilki."
    assert terms["kopek"].status == STATUS_UNANCHORED and terms["kopek"].mastery_level == 0
    annotations.delete_term(anchored.id)
    assert [t.word for t in annotations.list_terms(document.id)] == ["kopek"]
    with pytest.raises(InvalidAnnotationError):
        annotations.create_term(document.id, "", "x")
    with pytest.raises(NotFoundError):
        annotations.delete_term(loose.id + 100)


def test_deleting_the_document_cascades_to_its_annotations(session, annotations, resource_with_document):
    from pdfkit.infra.orm import PdfAnnotationRow, PdfDocumentRow, PdfResourceLinkRow

    resource, document, _p = resource_with_document
    annotations.create_highlight(document.id, "metin parcasi", [_segment("metin parcasi")])
    session.delete(session.get(PdfResourceLinkRow, resource.id))
    session.flush()
    session.delete(session.get(PdfDocumentRow, document.id))
    session.commit()

    assert session.query(PdfAnnotationRow).count() == 0
