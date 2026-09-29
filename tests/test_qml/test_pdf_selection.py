"""PDF secimi -> alinti/kelime akisi (page-point koordinatlari, karakter konumu, cumle baglami).

Onceden yalnizca `*Hybrid*.pdf` adli gercek bir dosya varsa calisan (fiilen hep atlanan) bir teste
dayaniyordu; artik tests/pdf_factory.py ile uretilen deterministik PDF kullanilir.
"""
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtPdf import QPdfDocument

from tests.pdf_factory import write_text_pdf
from ui_qml.bridge import QmlBridge


@pytest.fixture()
def pdf_env(qapp, session, tmp_path, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)
    pdf = write_text_pdf(tmp_path / "metin.pdf")
    url = pdf.as_uri()
    resource = bridge._controller.add_resource({"title": "PDF", "url": url, "category_id": None, "priority": 2})
    doc = bridge._load_pdf_document(url)
    assert doc is not None and doc.status() == QPdfDocument.Status.Ready
    return bridge, resource, url, doc


def _selection_for(doc, needle: str, page: int = 0) -> dict:
    """`needle` kelimesinin sayfadaki konumundan QML'in gonderecegi secim haritasini uretir."""
    text = doc.getSelectionAtIndex(page, 0, 100000).text()
    start = text.index(needle)
    rect = doc.getSelectionAtIndex(page, start, len(needle)).boundingRectangle()
    y = rect.y() + rect.height() / 2
    return {"page": page, "fromX": rect.x() + 0.5, "fromY": y, "toX": rect.x() + rect.width() - 0.5, "toY": y}


def test_test_pdf_is_readable_and_has_expected_text(pdf_env):
    _bridge, _resource, _url, doc = pdf_env

    assert doc.pageCount() == 1
    text = doc.getSelectionAtIndex(0, 0, 100000).text()
    assert "tilki" in text and "Ikinci satir" in text


def test_add_pdf_highlight_stores_text_and_char_position(pdf_env):
    bridge, resource, url, doc = pdf_env
    selection = _selection_for(doc, "tilki")

    bridge.addPdfHighlight(resource.id, url, selection, "#EAB308")

    (highlight,) = bridge._controller.load_resource_highlights(resource.id)
    assert highlight.content.strip() == "tilki"
    assert highlight.page_number == 0
    page_text = doc.getSelectionAtIndex(0, 0, 100000).text()
    assert highlight.start_index == page_text.index("tilki")
    assert highlight.length == len("tilki")


def test_stored_highlight_geometry_matches_the_selected_word(pdf_env):
    bridge, resource, url, doc = pdf_env
    selection = _selection_for(doc, "kopegin")
    bridge.addPdfHighlight(resource.id, url, selection, "#EAB308")
    bridge.openReader(resource.id)

    (item,) = bridge.currentReaderResource["highlights"]

    x, y, width, height = item["boundingRect"]
    assert x <= selection["fromX"] <= x + width and x <= selection["toX"] <= x + width
    assert y <= selection["fromY"] <= y + height  # kutu secilen satirin uzerinde
    assert item["boundsPolygons"]


def test_add_pdf_vocabulary_stores_sentence_context(pdf_env):
    bridge, resource, url, doc = pdf_env
    selection = _selection_for(doc, "tilki")

    bridge.addPdfVocabulary(resource.id, url, selection, "fox")

    (vocab,) = bridge._controller.get_resource(resource.id).vocabulary
    assert vocab.word == "tilki" and vocab.translation == "fox"
    assert vocab.context_sentence.startswith("Hizli kahverengi tilki")
    assert vocab.context_sentence.endswith("atlar.")
    assert "\n" not in vocab.context_sentence


def test_selection_over_blank_area_is_ignored(pdf_env):
    bridge, resource, url, _doc = pdf_env
    # Metin ust kenardan ~92pt asagida basliyor; 500pt asagisi bos alandir.
    blank = {"page": 0, "fromX": 300.0, "fromY": 500.0, "toX": 400.0, "toY": 500.0}

    bridge.addPdfHighlight(resource.id, url, blank, "#EAB308")
    bridge.addPdfVocabulary(resource.id, url, blank, "x")

    assert bridge._controller.load_resource_highlights(resource.id) == []
    assert bridge._controller.get_resource(resource.id).vocabulary == []


def test_unreadable_pdf_is_ignored(qapp, session, tmp_path):
    bridge = QmlBridge(session)
    resource = bridge._controller.add_resource({"title": "Bozuk", "url": (tmp_path / "yok.pdf").as_uri(),
                                                "category_id": None, "priority": 2})
    selection = {"page": 0, "fromX": 1.0, "fromY": 1.0, "toX": 2.0, "toY": 1.0}

    bridge.addPdfHighlight(resource.id, (tmp_path / "yok.pdf").as_uri(), selection, "#EAB308")

    assert bridge._controller.load_resource_highlights(resource.id) == []


def test_html_reader_highlight_position_map(qapp, session):
    bridge = QmlBridge(session)
    resource = bridge._controller.add_resource({"title": "Web", "url": "https://x.org/a", "category_id": None, "priority": 2})

    bridge.addHighlight(resource.id, "konumsuz", "#EAB308")  # HTML okuyucu: konum yok
    bridge.addHighlight(resource.id, "konumlu", "#EAB308", {"page": 1, "startIndex": 5, "length": 7})
    bridge.addHighlight(resource.id, "eksi", "#EAB308", {"page": -1, "startIndex": -1, "length": -1})

    by_content = {h.content: h for h in bridge._controller.load_resource_highlights(resource.id)}
    assert by_content["konumsuz"].page_number is None
    assert (by_content["konumlu"].page_number, by_content["konumlu"].start_index, by_content["konumlu"].length) == (1, 5, 7)
    assert by_content["eksi"].page_number is None  # -1 = konum yok
