"""Metin katmani olmayan (taranmis) PDF'te okuyucu uyari bandi gosterir; metinli PDF'te gostermez."""
import pytest

from tests.pdf_factory import write_outline_pdf, write_text_pdf
from tests.test_qml.qml_harness import SyncThreadPool, click, find_named, find_text, open_window, pump
from ui_qml.bridge import QmlBridge


@pytest.fixture()
def env(qapp, session, tmp_path, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "metinli.pdf").as_uri())
    bridge.library.importLocalPdf(write_outline_pdf(tmp_path / "taranmis.pdf", ["A", "B"]).as_uri())
    resources = {r.title: r for r in bridge.controllers.resources.load_resources_with_filters({})}
    engine, window = open_window(qapp, bridge, "showcase", width=1400, height=900)
    yield qapp, bridge, window, resources["metinli"], resources["taranmis"]
    del engine


def _banner_visible(window) -> bool:
    return bool(find_named(window, "noTextLayerBanner").property("visible"))


def test_banner_is_shown_for_a_pdf_without_a_text_layer_and_can_be_dismissed(env):
    qapp, bridge, window, _text, scanned = env

    bridge.reader.openReader(scanned.id)
    pump(qapp, 150)
    assert bridge.pdf.currentDocument["hasTextLayer"] is False
    assert _banner_visible(window)
    assert find_named(window, "noTextLayerBanner").property("height") == 40

    click(qapp, window, find_text(window, "Gizle"))
    pump(qapp, 30)

    assert not _banner_visible(window)
    assert find_named(window, "noTextLayerBanner").property("height") == 0


def test_banner_is_hidden_for_a_pdf_with_text(env):
    qapp, bridge, window, text, _scanned = env

    bridge.reader.openReader(text.id)
    pump(qapp, 150)

    assert bridge.pdf.currentDocument["hasTextLayer"] is True
    assert not _banner_visible(window)


def test_dismissal_applies_to_one_document_only(env):
    qapp, bridge, window, _text, scanned = env
    bridge.reader.openReader(scanned.id)
    pump(qapp, 150)
    click(qapp, window, find_text(window, "Gizle"))
    pump(qapp, 30)

    bridge.reader.closeReader()
    pump(qapp, 60)
    bridge.reader.openReader(scanned.id)
    pump(qapp, 150)

    assert _banner_visible(window)
