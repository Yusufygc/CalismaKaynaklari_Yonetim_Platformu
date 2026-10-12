"""Yazma yolu (bridge.pdf): gercek QPdfDocument secimleriyle alinti, not ve kelime islemleri."""
import time

import pytest
from PySide6.QtPdf import QPdfDocument

from pdfkit.api import PdfBridge
from pdfkit.domain.annotations import STATUS_OK, STATUS_ORPHANED, Segment
from pdfkit.ui import messages
from pdfkit.ui.pdf_text import current_engine_fp


@pytest.fixture()
def opened(qapp, resource_with_document, pdf_library):
    resource, document, path = resource_with_document
    bridge = PdfBridge(pdf_library)
    notes = []
    bridge.notification.connect(lambda kind, text: notes.append((kind, text)))
    changed = []
    bridge.contentChanged.connect(changed.append)
    assert bridge.openDocument(resource.id)
    reader = QPdfDocument()
    reader.load(str(path))
    yield bridge, document, reader, notes, changed
    reader.close()


def selection_of(reader, word, page=0):
    """QML'in gonderecegi secim haritasi: kelimenin sayfa noktasi uzayindaki sol-sag uclari."""
    text = reader.getSelectionAtIndex(page, 0, 1_000_000).text()
    start = text.index(word)
    rect = reader.getSelectionAtIndex(page, start, len(word)).boundingRectangle()
    y = rect.y() + rect.height() / 2
    return {"page": page, "fromX": rect.x() + 1, "fromY": y, "toX": rect.x() + rect.width() + 1, "toY": y}


def test_add_highlight_stores_ready_geometry_context_and_updates_the_model_incrementally(opened, pdf_library):
    bridge, document, reader, notes, changed = opened
    inserted = []
    bridge.annotations.rowsInserted.connect(lambda parent, first, last: inserted.append((first, last)))

    annotation_id = bridge.addHighlight(selection_of(reader, "tilki"), "finding")

    assert annotation_id > 0 and inserted == [(0, 0)]
    stored = pdf_library.annotations().get_highlight(annotation_id)
    assert "tilki" in stored.quote_exact and stored.label_key == "finding" and stored.status == STATUS_OK
    assert stored.segments[0].polygons  # secimden hazir geldi, getSelectionAtIndex gerekmedi
    assert stored.engine_fp == current_engine_fp()
    assert "kahverengi" in stored.quote_prefix and stored.quote_suffix
    assert bridge.annotations.count == 1 and bridge.pageModel(0).rowCount() == 1
    assert notes == [("info", messages.HIGHLIGHT_SAVED)] and changed == [bridge.currentDocument["resourceId"]]


def test_highlighting_the_same_text_again_relabels_instead_of_duplicating(opened, pdf_library):
    bridge, document, reader, notes, _changed = opened
    selection = selection_of(reader, "tembel")
    first = bridge.addHighlight(selection, "finding")

    second = bridge.addHighlight(selection, "critique")

    assert second == first and bridge.annotations.count == 1
    stored = pdf_library.annotations().get_highlight(first)
    assert stored.label_key == "critique" and stored.color is None
    assert notes[-1] == ("info", messages.HIGHLIGHT_RELABELED)


def test_blank_selection_or_closed_document_is_reported_not_crashed(opened):
    bridge, _document, reader, notes, changed = opened
    nowhere = {"page": 0, "fromX": 1.0, "fromY": 1.0, "toX": 2.0, "toY": 1.0}

    assert bridge.addHighlight(nowhere, "finding") == 0
    assert notes[-1] == ("error", messages.NO_SELECTION) and changed == []

    bridge.closeDocument()
    assert bridge.addHighlight(selection_of(reader, "tilki"), "finding") == 0
    assert bridge.addTerm(selection_of(reader, "tilki"), "fox") == 0


def test_label_comment_tags_and_delete_update_model_and_database(opened, pdf_library):
    bridge, _document, reader, _notes, _changed = opened
    annotation_id = bridge.addHighlight(selection_of(reader, "kopegin"), "important")

    assert bridge.setLabel(annotation_id, "method")
    assert bridge.setComment(annotation_id, "  yontem notu ")
    assert bridge.setTags(annotation_id, ["#Derin", "derin", "x"])

    row = bridge.annotations.index(0)
    roles = {bytes(n).decode(): r for r, n in bridge.annotations.roleNames().items()}
    assert bridge.annotations.data(row, roles["labelKey"]) == "method"
    assert bridge.annotations.data(row, roles["color"]) == "#06B6D4"
    assert bridge.annotations.data(row, roles["comment"]) == "yontem notu"
    assert bridge.annotations.data(row, roles["tags"]) == ["derin", "x"]
    assert pdf_library.annotations().get_highlight(annotation_id).comment == "yontem notu"

    assert bridge.deleteAnnotation(annotation_id)
    assert bridge.annotations.count == 0 and pdf_library.annotations().list_highlights(_document.id) == []
    assert not bridge.setComment(annotation_id, "yok")  # silinmis: hata bildirimi, istisna degil


def test_bulk_delete_removes_rows_and_reports_the_count(opened):
    bridge, _document, reader, notes, _changed = opened
    ids = [bridge.addHighlight(selection_of(reader, word), "finding") for word in ("tilki", "tembel", "kopegin")]

    assert bridge.deleteAnnotations(ids[:2] + [9999]) == 2

    assert bridge.annotations.count == 1
    assert notes[-1] == ("info", messages.HIGHLIGHTS_DELETED_FMT.format(count=2))


def test_page_notes_are_crud_through_models_and_page_filter(opened, pdf_library):
    bridge, document, _reader, notes, changed = opened

    note_id = bridge.addNote(0, 100.5, 200.25, "  Tekrar oku ")
    other = bridge.addNote(3, 10.0, 10.0, "baska sayfa")

    assert note_id > 0 and bridge.notes.count == 2
    assert bridge.notePageModel(0).rowCount() == 1 and bridge.notePageModel(3).rowCount() == 1
    assert bridge.updateNote(note_id, "Guncel")
    assert pdf_library.annotations().list_notes(document.id)[0].text == "Guncel"
    assert bridge.deleteNote(other) and bridge.notes.count == 1
    assert bridge.addNote(0, 1.0, 1.0, "   ") == 0 and notes[-1][0] == "error"
    assert len(changed) == 4  # 2 ekleme + guncelleme + silme; basarisiz (bos) not sayilmaz


def test_terms_keep_position_and_sentence_context_and_notify_the_property(opened, pdf_library):
    bridge, document, reader, notes, _changed = opened
    term_changes = []
    bridge.termsChanged.connect(lambda: term_changes.append(1))

    term_id = bridge.addTerm(selection_of(reader, "tilki"), "  fox ")

    assert term_id > 0 and term_changes == [1]
    (term,) = bridge.terms
    assert term["word"].strip().startswith("tilki") and term["translation"] == "fox" and term["page"] == 0
    assert "Hizli kahverengi tilki" in term["context"] and term["context"].endswith("atlar.")
    assert notes[-1][0] == "info" and "kelime havuzuna eklendi" in notes[-1][1]
    stored = pdf_library.annotations().list_terms(document.id)[0]
    assert stored.status == STATUS_OK and stored.segments[0].polygons

    assert bridge.deleteTerm(term_id) and bridge.terms == [] and term_changes == [1, 1]


def test_empty_translation_is_rejected_with_an_error_message(opened):
    bridge, _document, reader, notes, _changed = opened

    assert bridge.addTerm(selection_of(reader, "tilki"), "   ") == 0
    assert notes[-1][0] == "error"


def test_unexpected_failure_is_logged_and_reported_without_touching_the_model(opened, pdf_library, monkeypatch):
    bridge, _document, reader, notes, changed = opened

    def boom(*args, **kwargs):
        raise RuntimeError("disk dolu")

    monkeypatch.setattr("pdfkit.app.annotations.AnnotationService.create_highlight", boom)

    assert bridge.addHighlight(selection_of(reader, "tilki"), "finding") == 0
    assert notes[-1] == ("error", messages.OPERATION_FAILED) and bridge.annotations.count == 0 and changed == []


def test_adding_a_highlight_stays_fast_with_a_thousand_existing_annotations(opened, pdf_library):
    """Faz 3b butcesi: tek alinti ekleme <=16 ms (CI dalgalanmasina karsi esik 4x gevsek)."""
    bridge, document, reader, _notes, _changed = opened
    service = pdf_library.annotations()
    for i in range(1000):
        service.create_highlight(
            document.id, f"alinti {i}", [Segment(0, 500 + i, 505 + i, f"alinti {i}", [[(1.0, 2.0), (3.0, 4.0)]])],
            engine_fp=current_engine_fp(),
        )
    bridge.openDocument(bridge.currentDocument["resourceId"])  # 1000 alintiyi modele yukle
    selection = selection_of(reader, "kahverengi")

    started = time.perf_counter()
    assert bridge.addHighlight(selection, "finding") > 0
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert bridge.annotations.count == 1001
    assert elapsed_ms < 64, f"alinti ekleme {elapsed_ms:.1f} ms"


def test_notebook_items_merge_highlights_and_notes_sorted_by_page_and_filtered_by_label(opened):
    bridge, _document, reader, _notes, _changed = opened
    revisions = []
    bridge.revisionChanged.connect(lambda: revisions.append(bridge.revision))
    bridge.addHighlight(selection_of(reader, "kopegin"), "method")
    bridge.addHighlight(selection_of(reader, "tilki"), "finding")
    bridge.addNote(0, 5.0, 5.0, "ust not")
    bridge.addNote(2, 5.0, 5.0, "sonraki sayfa")

    everything = bridge.notebookItems("", "", False, bridge.revision)
    methods_only = bridge.notebookItems("method", "", False, bridge.revision)

    assert [(i["kind"], i["page"]) for i in everything] == [("note", 0), ("highlight", 0), ("highlight", 0), ("note", 2)]
    assert [i["text"] for i in everything if i["kind"] == "highlight"][0].strip().startswith("tilki")
    assert everything[0]["color"] == "" and everything[1]["color"] in {"#22C55E", "#06B6D4"} and everything[1]["y"] >= 0
    assert [i["label"] for i in methods_only] == ["Yöntem"]  # etiket filtresi notlari da disarida birakir
    assert revisions == sorted(revisions) and len(set(revisions)) == len(revisions) >= 4  # her yazma revizyonu artirir


def _orphan(pdf_library, document, comment="onemli yorum", tags=("yontem",)):
    """Konumu bulunamayan (metni belgeden silinmis) bir alinti; yorum, etiket ve anlam etiketi dolu."""
    return pdf_library.annotations().create_highlight(
        document.id, "belgede artik olmayan metin", [Segment(0, 1, 28, "belgede artik olmayan metin")],
        "critique", comment=comment, tags=list(tags), status=STATUS_ORPHANED,
    )


def test_orphans_are_counted_listed_and_filterable_in_the_notebook(opened, pdf_library):
    bridge, document, reader, _notes, _changed = opened
    bridge.addHighlight(selection_of(reader, "tilki"), "finding")
    orphan = _orphan(pdf_library, document)
    bridge.openDocument(bridge.currentDocument["resourceId"])  # modeli yeniden yukle

    items = bridge.notebookItems("", "", True, bridge.revision)

    assert bridge.orphanCount == 1
    assert [i["id"] for i in items] == [orphan.id] and items[0]["status"] == STATUS_ORPHANED
    assert items[0]["x"] == -1 and items[0]["tags"] == ["yontem"]  # sayfada cizilemez: konum yok


def test_relink_attaches_an_orphan_to_the_new_selection_keeping_label_comment_and_tags(opened, pdf_library):
    bridge, document, reader, notes, changed = opened
    orphan = _orphan(pdf_library, document)
    bridge.openDocument(bridge.currentDocument["resourceId"])
    changed.clear()
    notes.clear()

    assert bridge.relinkAnnotation(orphan.id, selection_of(reader, "tembel"))

    stored = pdf_library.annotations().get_highlight(orphan.id)
    assert stored.status == STATUS_OK and "tembel" in stored.quote_exact
    assert stored.segments[0].polygons and stored.engine_fp == current_engine_fp()
    assert stored.quote_prefix and stored.quote_suffix  # baglam da yeni metinden
    assert (stored.label_key, stored.comment, stored.tags) == ("critique", "onemli yorum", ["yontem"])
    assert bridge.orphanCount == 0 and bridge.annotations.count == 1
    assert bridge.pageModel(0).rowCount() == 1  # artik sayfada cizilir
    assert notes == [("info", messages.HIGHLIGHT_RELINKED)] and changed == [bridge.currentDocument["resourceId"]]


def test_relink_without_a_usable_selection_reports_an_error_and_keeps_the_orphan(opened, pdf_library):
    bridge, document, _reader, notes, changed = opened
    orphan = _orphan(pdf_library, document)
    bridge.openDocument(bridge.currentDocument["resourceId"])
    changed.clear()
    notes.clear()

    assert not bridge.relinkAnnotation(orphan.id, {"page": 0, "fromX": 1.0, "fromY": 1.0, "toX": 2.0, "toY": 1.0})

    assert pdf_library.annotations().get_highlight(orphan.id).status == STATUS_ORPHANED
    assert notes == [("error", messages.NO_SELECTION)] and changed == []


def test_relinking_an_unknown_annotation_fails_without_touching_other_data(opened):
    bridge, _document, reader, notes, _changed = opened

    assert not bridge.relinkAnnotation(99999, selection_of(reader, "tilki"))

    assert notes[-1][0] == "error" and bridge.annotations.count == 0


def test_free_tags_are_listed_with_counts_and_filter_the_notebook(opened):
    bridge, _document, reader, _notes, _changed = opened
    first = bridge.addHighlight(selection_of(reader, "tilki"), "finding")
    second = bridge.addHighlight(selection_of(reader, "tembel"), "method")
    bridge.addHighlight(selection_of(reader, "kopegin"), "method")
    bridge.setTags(first, ["#Hipotez", "ornek"])
    bridge.setTags(second, ["hipotez"])

    assert bridge.tags == [{"name": "hipotez", "count": 2}, {"name": "ornek", "count": 1}]  # # atilir, kucuk harfe
    tagged = bridge.notebookItems("", "hipotez", False, bridge.revision)
    assert {i["id"] for i in tagged} == {first, second}
    assert [i["tags"] for i in bridge.notebookItems("method", "hipotez", False, bridge.revision)] == [["hipotez"]]
    assert bridge.notebookItems("", "yok", False, bridge.revision) == []
