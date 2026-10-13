"""Uygulama baglantisi: ice aktarilan PDF kendiliginden tam metin dizinine girer; acilista eksikler taranir."""
import pytest
from PySide6.QtTest import QTest

from tests.pdf_factory import write_multipage_text_pdf
from tests.test_qml.qml_harness import SyncThreadPool
from ui_qml.bridge import QmlBridge

PAGES = [
    ["Kuantum bilgisayarlar hakkinda giris bolumu. Bu makale temel kavramlari anlatir."],
    ["Ikinci sayfa: cocuklarin ogrenme sekli ve motivasyon uzerine bir tartisma."],
]


def _make_bridge(session, tmp_path, monkeypatch, auto_index):
    monkeypatch.setattr("ui_qml.context.AUTO_INDEX", auto_index)  # conftest kapatir; bu dosya baglantiyi sinar
    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    instance = QmlBridge(session)
    instance.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(instance.ctx.extractor, "schedule", lambda *args: None)
    return instance


@pytest.fixture()
def bridge(qapp, session, tmp_path, monkeypatch):
    return _make_bridge(session, tmp_path, monkeypatch, auto_index=True)


def _wait_idle(bridge, timeout=5000):
    waited = 0
    while bridge.ctx.text_indexer.status()["pending"] or waited == 0:
        QTest.qWait(20)
        waited += 20
        assert waited < timeout


def test_an_imported_pdf_becomes_searchable_without_any_user_action(bridge, tmp_path):
    bridge.library.importLocalPdf(write_multipage_text_pdf(tmp_path / "makale.pdf", PAGES).as_uri())
    _wait_idle(bridge)
    QTest.qWait(30)

    hits = bridge.ctx.pdf_library.searching().search("ogrenme sekli")

    assert [h.page for h in hits] == [1]


def test_startup_scan_indexes_documents_that_were_imported_before_the_index_existed(qapp, session, tmp_path, monkeypatch):
    bridge = _make_bridge(session, tmp_path, monkeypatch, auto_index=False)  # ice aktarma dizinlemeyi tetiklemez
    bridge.library.importLocalPdf(write_multipage_text_pdf(tmp_path / "eski.pdf", PAGES).as_uri())
    QTest.qWait(50)
    assert bridge.ctx.pdf_library.searching().search("kuantum") == []  # henuz dizinlenmedi

    bridge.ctx.text_indexer.scan()  # acilistaki bakimin (legacyAdoptionFinished) yaptigi sey
    _wait_idle(bridge)
    QTest.qWait(30)

    assert len(bridge.ctx.pdf_library.searching().search("kuantum")) == 1


def test_adoption_finishing_triggers_the_startup_scan(qapp, session, tmp_path, monkeypatch):
    bridge = _make_bridge(session, tmp_path, monkeypatch, auto_index=True)
    scans = []
    monkeypatch.setattr(bridge.ctx.text_indexer, "scan", lambda: scans.append(1))

    bridge.ctx.pdf_library.legacyAdoptionFinished.emit(0)

    assert scans == [1]
