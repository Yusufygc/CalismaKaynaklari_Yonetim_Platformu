"""Metin okuyucusu: vurgulama (secim cubugu secime yakin, renk kaydi, boyama), icerik durumu, PDF tespiti, acik erisim."""
from unittest.mock import patch

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject

from tests.test_qml.qml_harness import SyncThreadPool, click, find_named, open_window, pump, walk
from ui_qml.bridge import QmlBridge

LONG_TEXT = "".join(
    f"<p>Paragraf {i}: derin ogrenme yontemleri hisse senedi fiyat tahmininde kullanilir ve basarilidir.</p>" for i in range(40)
)


@pytest.fixture()
def bridge(qapp, session, monkeypatch):
    instance = QmlBridge(session)
    instance.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(instance.ctx.extractor, "schedule", lambda *args: None)
    return instance


def _add(bridge, url="https://example.org/makale", full_text=None, **extra):
    resource = bridge.controllers.resources.add_resource({"title": "Makale", "url": url, "category_id": None, "priority": 2, **extra})
    if full_text:
        bridge.controllers.resources.update_resource(resource.id, {"full_text": full_text})
    return resource


def _visible(window, name):
    return [i for i in walk(window.contentItem()) if i.objectName() == name and i.isVisible()]


def _select(text, start, end):
    QMetaObject.invokeMethod(text, "select", Q_ARG(int, start), Q_ARG(int, end))


def _flickable(window):
    return next(i for i in walk(window.contentItem()) if i.property("contentY") is not None and i.property("contentHeight") > window.height())


# ---- vurgulama ----


def test_clicking_a_color_saves_the_highlight_paints_it_and_the_bar_sits_next_to_the_selection(bridge, qapp):
    resource = _add(bridge, full_text=LONG_TEXT)
    bridge.reader.openReader(resource.id)
    engine, window = open_window(qapp, bridge, "reader", width=1300, height=900)
    pump(qapp, 20)
    text, bar = find_named(window, "readerText"), find_named(window, "selectionBar")
    assert text.isVisible() and not bar.isVisible()

    _select(text, 200, 260)
    pump(qapp, 10)

    assert bar.isVisible()
    assert bar.y() < window.height() * 0.6  # sayfanin en altinda degil: secilen metnin yaninda
    dots = _visible(window, "highlightColorDot")
    assert len(dots) == 5
    dot_y = dots[0].mapToScene(dots[0].boundingRect().center()).y()
    assert abs(dot_y - bar.mapToScene(bar.boundingRect().center()).y()) <= 2  # renk noktalari cubugun dikey ortasinda

    click(qapp, window, dots[0])
    pump(qapp, 20)

    saved = bridge.controllers.resources.get_resource(resource.id).highlights
    assert len(saved) == 1 and saved[0].color.upper() == "#EAB308" and saved[0].content
    assert "background-color:#EAB308" in bridge.reader.readerHtml  # metin uzerinde boyandi
    assert engine.captured_warnings == []


def test_the_selection_bar_follows_the_selection_and_hides_when_it_scrolls_out_of_view(bridge, qapp):
    resource = _add(bridge, full_text=LONG_TEXT)
    bridge.reader.openReader(resource.id)
    engine, window = open_window(qapp, bridge, "reader", width=1300, height=900)
    pump(qapp, 20)
    text, bar = find_named(window, "readerText"), find_named(window, "selectionBar")
    _select(text, 100, 160)
    pump(qapp, 10)
    assert bar.isVisible()
    flick = _flickable(window)
    flick.setProperty("contentY", flick.property("contentHeight") - flick.height())  # secim gorunur alanin ustune kaydi
    pump(qapp, 10)

    assert not bar.isVisible()  # cubuk ekranin altinda/ustunde asili kalmaz
    assert engine.captured_warnings == []


# ---- icerik durumu ----


def test_content_state_distinguishes_loading_failure_and_ready(bridge, qapp):
    resource = _add(bridge)
    bridge.reader.openReader(resource.id)
    assert bridge.reader.extractionState == "empty"

    bridge.ctx.extractor._pending.add(resource.id)
    assert bridge.reader.extractionState == "pending"
    bridge.ctx.extractor._pending.discard(resource.id)
    bridge.ctx.extractor._failed.add(resource.id)
    assert bridge.reader.extractionState == "failed"

    bridge.controllers.resources.update_resource(resource.id, {"full_text": "<p>metin</p>"})
    bridge.reader.refresh_current(resource.id)
    assert bridge.reader.extractionState == "ready"


def test_the_status_panel_replaces_the_endless_loading_text_and_offers_actions(bridge, qapp):
    resource = _add(bridge, url="https://doi.org/10.1016/j.future.2013.01.010")
    bridge.reader.openReader(resource.id)
    bridge.ctx.extractor._failed.add(resource.id)
    bridge.reader.refresh_current(resource.id)
    engine, window = open_window(qapp, bridge, "reader", width=1300, height=900)
    pump(qapp, 20)

    assert bridge.reader.readerDoi == "10.1016/j.future.2013.01.010"
    assert find_named(window, "readerStatusText").property("text") == "Sayfanın metni alınamadı"
    assert not find_named(window, "readerText").isVisible()
    assert _visible(window, "findOpenAccessButton") and _visible(window, "retryExtractionButton") and _visible(window, "openInBrowserButton")
    assert engine.captured_warnings == []


# ---- PDF tespiti ve acik erisim ----


def test_a_page_that_turns_out_to_be_a_pdf_is_flagged_and_opens_in_the_pdf_reader(bridge, qapp):
    resource = _add(bridge, url="https://dergipark.org.tr/tr/download/article-file/123")
    bridge.reader.openReader(resource.id)
    assert bridge.currentView == "reader"
    downloads = []
    bridge.ctx.pdf_files.start_download = lambda res, url=None: downloads.append((res.id, url))

    bridge.ctx.extractor.pdfDetected.emit(resource.id)

    saved = bridge.controllers.resources.get_resource(resource.id)
    assert bridge.currentView == "pdfReader" and downloads == [(resource.id, None)]
    assert saved.extra_metadata["remote_pdf"] is True
    assert bridge.ctx.pdf_files.remote_pdf_url(saved) == resource.url  # sonraki acilis dogrudan PDF


def test_an_open_access_copy_is_looked_up_automatically_when_a_doi_page_cannot_be_read(bridge, qapp):
    resource = _add(bridge, url="https://doi.org/10.1016/j.future.2013.01.010")
    bridge.reader.openReader(resource.id)
    downloads = []
    bridge.ctx.pdf_files.start_download = lambda res, url=None: downloads.append(url)

    with patch("workers.open_access_worker.OpenAccessService") as service:
        service.return_value.find_pdf_url.return_value = "https://arxiv.org/pdf/1207.0203"
        bridge.ctx.extractor._failed.add(resource.id)
        bridge.ctx.extractor.statusChanged.emit(resource.id)  # cikarim basarisiz bitti

    saved = bridge.controllers.resources.get_resource(resource.id)
    assert downloads == ["https://arxiv.org/pdf/1207.0203"] and bridge.currentView == "pdfReader"
    assert saved.extra_metadata["oa_pdf_url"] == "https://arxiv.org/pdf/1207.0203"
    assert bridge.ctx.pdf_files.remote_pdf_url(saved) == "https://arxiv.org/pdf/1207.0203"


def test_when_no_open_access_copy_exists_the_state_says_so_and_nothing_is_downloaded(bridge, qapp):
    resource = _add(bridge, url="https://doi.org/10.1016/j.future.2013.01.010")
    bridge.reader.openReader(resource.id)
    downloads = []
    bridge.ctx.pdf_files.start_download = lambda res, url=None: downloads.append(url)

    with patch("workers.open_access_worker.OpenAccessService") as service:
        service.return_value.find_pdf_url.return_value = None
        bridge.ctx.extractor._failed.add(resource.id)
        bridge.ctx.extractor.statusChanged.emit(resource.id)

    assert bridge.reader.extractionState == "noOpenAccess" and downloads == [] and bridge.currentView == "reader"


def test_a_resource_without_a_doi_never_searches_for_open_access(bridge, qapp):
    resource = _add(bridge, url="https://example.org/yazi")
    bridge.reader.openReader(resource.id)
    with patch("workers.open_access_worker.OpenAccessService") as service:
        bridge.ctx.extractor._failed.add(resource.id)
        bridge.ctx.extractor.statusChanged.emit(resource.id)
        bridge.reader.findOpenAccessPdf()
    service.assert_not_called()
    assert bridge.reader.readerDoi == "" and bridge.reader.extractionState == "failed"


def test_old_pdf_text_without_the_new_paragraph_format_is_re_extracted_once(bridge, qapp, monkeypatch):
    scheduled = []
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda rid, url: scheduled.append(rid))
    old = _add(bridge, full_text="<h3>Sayfa 1</h3><p>eski tek paragraf</p>")
    current = _add(bridge, url="https://example.org/b", full_text="<h3>Sayfa 1</h3><p>yeni</p>", extra_metadata={"reflow": 2})
    plain = _add(bridge, url="https://example.org/c", full_text="<p>normal makale</p>")

    for resource in (old, current, plain):
        bridge.reader.openReader(resource.id)

    assert scheduled == [old.id]
