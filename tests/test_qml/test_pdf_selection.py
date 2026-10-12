"""PDF secimi -> alinti/kelime akisi (page-point koordinatlari, karakter konumu, cumle baglami) pdfkit uzerinden.

tests/pdf_factory.py ile uretilen deterministik PDF kullanilir.
"""
import pytest
from PySide6.QtPdf import QPdfDocument

from tests.pdf_factory import write_text_pdf
from tests.test_qml.qml_harness import SyncThreadPool
from ui_qml.bridge import QmlBridge


@pytest.fixture()
def pdf_env(qapp, session, tmp_path, monkeypatch):
    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "metin.pdf").as_uri())
    (resource,) = bridge.controllers.resources.load_resources_with_filters({})
    assert bridge.pdf.openDocument(resource.id)
    doc = QPdfDocument()
    doc.load(str(_path_of(bridge)))
    assert doc.status() == QPdfDocument.Status.Ready
    return bridge, resource, doc


def _path_of(bridge):
    document = bridge.ctx.pdf_library.documents().document_for_resource(bridge.pdf.currentDocument["resourceId"])
    return bridge.ctx.pdf_library.file_path(document)


def _selection_for(doc, needle: str, page: int = 0) -> dict:
    """`needle` kelimesinin sayfadaki konumundan QML'in gonderecegi secim haritasini uretir."""
    text = doc.getSelectionAtIndex(page, 0, 100000).text()
    start = text.index(needle)
    rect = doc.getSelectionAtIndex(page, start, len(needle)).boundingRectangle()
    y = rect.y() + rect.height() / 2
    return {"page": page, "fromX": rect.x() + 0.5, "fromY": y, "toX": rect.x() + rect.width() - 0.5, "toY": y}


def _annotations(bridge):
    return bridge.ctx.pdf_library.annotations(), bridge.pdf.currentDocument["documentId"]


def test_test_pdf_is_readable_and_has_expected_text(pdf_env):
    _bridge, _resource, doc = pdf_env

    assert doc.pageCount() == 1
    text = doc.getSelectionAtIndex(0, 0, 100000).text()
    assert "tilki" in text and "Ikinci satir" in text


def test_add_highlight_stores_text_and_char_position(pdf_env):
    bridge, _resource, doc = pdf_env
    selection = _selection_for(doc, "tilki")

    assert bridge.pdf.addHighlight(selection, "important") > 0

    service, document_id = _annotations(bridge)
    (highlight,) = service.list_highlights(document_id)
    assert highlight.quote_exact.strip() == "tilki"
    page_text = doc.getSelectionAtIndex(0, 0, 100000).text()
    segment = highlight.segments[0]
    assert segment.page == 0 and segment.start == page_text.index("tilki")
    assert segment.end - segment.start == len("tilki")


def test_stored_highlight_geometry_matches_the_selected_word(pdf_env):
    bridge, _resource, doc = pdf_env
    selection = _selection_for(doc, "kopegin")
    bridge.pdf.addHighlight(selection, "important")

    row = bridge.pdf.annotations.index(0)
    roles = {bytes(name).decode(): role for role, name in bridge.pdf.annotations.roleNames().items()}
    x, y, width, height = bridge.pdf.annotations.data(row, roles["boundingRect"])

    assert x <= selection["fromX"] <= x + width and x <= selection["toX"] <= x + width
    assert y <= selection["fromY"] <= y + height  # kutu secilen satirin uzerinde
    assert bridge.pdf.annotations.data(row, roles["polygons"])


def test_add_term_stores_sentence_context_and_position(pdf_env):
    bridge, _resource, doc = pdf_env

    assert bridge.pdf.addTerm(_selection_for(doc, "tilki"), "fox") > 0

    service, document_id = _annotations(bridge)
    (term,) = service.list_terms(document_id)
    assert term.word == "tilki" and term.translation == "fox"
    assert term.context_sentence.startswith("Hizli kahverengi tilki") and term.context_sentence.endswith("atlar.")
    assert "\n" not in term.context_sentence
    assert term.segments[0].page == 0


def test_selection_over_blank_area_is_ignored(pdf_env):
    bridge, _resource, _doc = pdf_env
    # Metin ust kenardan ~92pt asagida basliyor; 500pt asagisi bos alandir.
    blank = {"page": 0, "fromX": 300.0, "fromY": 500.0, "toX": 400.0, "toY": 500.0}

    assert bridge.pdf.addHighlight(blank, "important") == 0
    assert bridge.pdf.addTerm(blank, "x") == 0

    service, document_id = _annotations(bridge)
    assert service.list_highlights(document_id) == [] and service.list_terms(document_id) == []


def test_unreadable_pdf_cannot_be_opened_and_selections_are_ignored(qapp, session, tmp_path):
    bridge = QmlBridge(session)
    resource = bridge.controllers.resources.add_resource(
        {"title": "Bozuk", "url": (tmp_path / "yok.pdf").as_uri(), "category_id": None, "priority": 2}
    )
    selection = {"page": 0, "fromX": 1.0, "fromY": 1.0, "toX": 2.0, "toY": 1.0}

    assert bridge.pdf.openDocument(resource.id) is False
    assert bridge.pdf.addHighlight(selection, "important") == 0
    assert bridge.controllers.highlights.load_resource_highlights(resource.id) == []


def test_html_reader_highlight_position_map(qapp, session):
    bridge = QmlBridge(session)
    resource = bridge.controllers.resources.add_resource({"title": "Web", "url": "https://x.org/a", "category_id": None, "priority": 2})

    bridge.annotations.addHighlight(resource.id, "konumsuz", "#EAB308")  # HTML okuyucu: konum yok
    bridge.annotations.addHighlight(resource.id, "konumlu", "#EAB308", {"page": 1, "startIndex": 5, "length": 7})
    bridge.annotations.addHighlight(resource.id, "eksi", "#EAB308", {"page": -1, "startIndex": -1, "length": -1})

    by_content = {h.content: h for h in bridge.controllers.highlights.load_resource_highlights(resource.id)}
    assert by_content["konumsuz"].page_number is None
    assert (by_content["konumlu"].page_number, by_content["konumlu"].start_index, by_content["konumlu"].length) == (1, 5, 7)
    assert by_content["eksi"].page_number is None  # -1 = konum yok
