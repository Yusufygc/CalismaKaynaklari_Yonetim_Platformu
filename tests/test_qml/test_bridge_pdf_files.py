"""Yerel/web PDF kaynaklari: ice aktarma, indirme, silme ve okuyucuya dusme."""
import pytest

from tests.test_qml.qml_harness import SyncThreadPool
from ui_qml.bridge import QmlBridge


@pytest.fixture()
def local_pdf_env(qapp, session, monkeypatch, tmp_path):
    """Yerel PDF ice aktarma ortami: senkron havuz, gecici depolama dizini, diskte orijinal PDF.
    (bridge, storage_dir, original) dondurur."""
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)

    storage_dir = tmp_path / "pdf_storage"

    def _fake_pdf_storage_dir():
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", _fake_pdf_storage_dir)

    original = tmp_path / "orijinal_makale.pdf"
    original.write_bytes(b"%PDF-1.4 fake bytes")
    bridge.ctx.thread_pool = SyncThreadPool()
    return bridge, storage_dir, original


def test_qml_bridge_import_local_pdf_copies_and_creates_resource(local_pdf_env):
    bridge, storage_dir, original = local_pdf_env
    results = []
    bridge.library.pdfImportFinished.connect(results.append)

    bridge.library.importLocalPdf(original.as_uri())

    assert results == [True]
    assert bridge.library.resourcesModel.rowCount() == 1
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    assert resource.title == "orijinal_makale"
    assert resource.extra_metadata["source"] == "local_pdf"
    assert resource.extra_metadata["original_filename"] == "orijinal_makale.pdf"
    assert resource.url.startswith("file://")

    # Orijinal dosya yerinde durmali (kopya, tasima degil).
    assert original.exists()
    # Kopya storage dizininde olusmus olmali.
    copied_files = list(storage_dir.glob("*.pdf"))
    assert len(copied_files) == 1
    assert copied_files[0].name.endswith("orijinal_makale.pdf")


def test_qml_bridge_delete_resource_removes_copied_local_pdf(local_pdf_env):
    """Yerel PDF kaynagi silinince kopyalanan dosya da diskten kalkmali,
    QPdfDocument onbellegi de temizlenmeli -- aksi halde her import/delete
    dongusunde disk/RAM sizintisi birikiyordu (bkz. code review bulgusu)."""
    bridge, storage_dir, original = local_pdf_env
    bridge.library.importLocalPdf(original.as_uri())

    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    copied_path = list(storage_dir.glob("*.pdf"))[0]
    assert copied_path.exists()

    # Onbellege gercek bir QPdfDocument koymaya gerek yok -- sadece anahtarin
    # (url) silme sonrasi temizlendigini dogrulamak icin sahte bir deger yeterli.
    bridge.ctx.pdf_files._document_cache[resource.url] = object()

    bridge.library.deleteResource(resource.id)

    assert not copied_path.exists()
    assert resource.url not in bridge.ctx.pdf_files._document_cache


def _add_web_pdf_resource(bridge, url="https://arxiv.org/pdf/1706.03762"):
    return bridge.controllers.resources.add_resource(
        {"title": "Attention", "url": url, "category_id": None, "priority": 2}
    )


def test_qml_bridge_open_reader_downloads_web_pdf_then_serves_native(qapp, session, monkeypatch, tmp_path):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    started = []
    monkeypatch.setattr(bridge.ctx.pdf_files, "start_download", lambda res: started.append(res.id))
    res = _add_web_pdf_resource(bridge)

    bridge.reader.openReader(res.id)

    assert bridge.currentView == "pdfReader"
    assert started == [res.id]
    assert bridge.reader.currentReaderResource["pdfFileUrl"] == ""

    pdf = tmp_path / "attention.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    bridge.reader._on_pdf_download_finished(res.id, str(pdf))

    assert bridge.reader.currentReaderResource["pdfFileUrl"] == pdf.as_uri()
    assert bridge.reader.currentReaderResource["pdfState"] == "ready"
    # Ikinci acilista tekrar indirme baslamamali.
    started.clear()
    bridge.reader.openReader(res.id)
    assert started == []
    assert bridge.currentView == "pdfReader"


def test_qml_bridge_web_pdf_download_failure_falls_back_to_text_reader(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    monkeypatch.setattr(bridge.ctx.pdf_files, "start_download", lambda res: None)
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))
    res = _add_web_pdf_resource(bridge)

    bridge.reader.openReader(res.id)
    assert bridge.currentView == "pdfReader"
    bridge.reader._on_pdf_download_finished(res.id, None)

    assert bridge.currentView == "reader"
    assert notifications and notifications[-1][0] == "error"
    # Basarisiz kaynak icin tekrar acinca indirme denenmez, dogrudan metin okuyucu.
    bridge.reader.openReader(res.id)
    assert bridge.currentView == "reader"


def test_qml_bridge_delete_removes_downloaded_web_pdf(qapp, session, monkeypatch, tmp_path):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    storage = tmp_path / "store"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    res = _add_web_pdf_resource(bridge)
    pdf = storage / "abc_attention.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    bridge.reader._on_pdf_download_finished(res.id, str(pdf))

    bridge.library.deleteResource(res.id)

    assert not pdf.exists()


def test_qml_bridge_import_local_pdf_rejects_non_pdf(qapp, session, monkeypatch, tmp_path):
    bridge = QmlBridge(session)

    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    not_pdf = tmp_path / "not_a_pdf.txt"
    not_pdf.write_text("merhaba")

    results = []
    bridge.library.pdfImportFinished.connect(results.append)

    bridge.library.importLocalPdf(not_pdf.as_uri())

    assert results == [False]
    assert bridge.library.resourcesModel.rowCount() == 0
    assert notifications and notifications[0][0] == "error"
