import pytest

from ui_qml.bridge import QmlBridge


class _SyncThreadPool:
    def start(self, worker) -> None:
        worker.run()


class _RecordingPool:
    """Worker'lari calistirmadan biriktirir (arka plan islerinin UI thread'inde kosmadigini gosterir)."""

    def __init__(self) -> None:
        self.workers = []

    def start(self, worker) -> None:
        self.workers.append(worker)


@pytest.fixture()
def bridge(qapp, session, monkeypatch):
    b = QmlBridge(session)
    monkeypatch.setattr(b, "_schedule_full_text_extract", lambda *args: None)
    return b


def _fake_pdf_storage(monkeypatch, tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.bridge.pdf_storage_dir", lambda: storage)
    return storage


# ---------------------------------------------------------------- PDF import
def test_import_does_not_copy_on_the_calling_thread(bridge, monkeypatch, tmp_path):
    storage = _fake_pdf_storage(monkeypatch, tmp_path)
    pool = _RecordingPool()
    monkeypatch.setattr(bridge, "_thread_pool", pool)
    original = tmp_path / "buyuk.pdf"
    original.write_bytes(b"%PDF-1.4 x")
    results = []
    bridge.pdfImportFinished.connect(results.append)

    bridge.importLocalPdf(original.as_uri())

    assert len(pool.workers) == 1  # is worker'a verildi
    assert list(storage.glob("*.pdf")) == []  # henuz kopyalanmadi (UI thread'i bloklanmadi)
    assert results == []  # sonuc worker bitince gelir

    pool.workers[0].run()
    assert results == [True] and len(list(storage.glob("*.pdf"))) == 1


def test_import_copy_failure_reports_error_and_creates_no_resource(bridge, monkeypatch, tmp_path):
    _fake_pdf_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())
    original = tmp_path / "a.pdf"
    original.write_bytes(b"%PDF-1.4 x")

    def broken_copy(src, dst):
        raise OSError("disk dolu")

    monkeypatch.setattr("workers.pdf_import_worker.shutil.copyfile", broken_copy)
    notes, results = [], []
    bridge.notificationEmitted.connect(lambda kind, msg: notes.append(kind))
    bridge.pdfImportFinished.connect(results.append)

    bridge.importLocalPdf(original.as_uri())

    assert results == [False] and notes == ["error"]
    assert bridge.resourcesModel.rowCount() == 0


def test_import_signal_fires_once_per_call_for_multiple_files(bridge, monkeypatch, tmp_path):
    _fake_pdf_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())
    results = []
    bridge.pdfImportFinished.connect(results.append)
    files = []
    for name in ("a.pdf", "b.pdf"):
        f = tmp_path / name
        f.write_bytes(b"%PDF-1.4 x")
        files.append(f)
    bad = tmp_path / "c.txt"
    bad.write_text("x")

    for f in (*files, bad):
        bridge.importLocalPdf(f.as_uri())

    assert results == [True, True, False]


# ---------------------------------------------------------------- PDF outline
def test_load_pdf_outline_runs_in_background_and_caches(bridge, monkeypatch, tmp_path):
    pdf = tmp_path / "anahatli.pdf"
    pdf.write_bytes(b"%PDF-1.4 x")
    url = pdf.as_uri()
    calls = []
    monkeypatch.setattr(
        "workers.pdf_outline_worker.read_outline",
        lambda path: calls.append(path) or [{"title": "Giris", "level": 0, "page": 0}],
    )
    pool = _RecordingPool()
    monkeypatch.setattr(bridge, "_thread_pool", pool)
    changes = []
    bridge.pdfOutlinesChanged.connect(lambda: changes.append(1))

    bridge.loadPdfOutline(url)
    bridge.loadPdfOutline(url)  # yukleme suruyor: ikinci is baslamaz

    assert len(pool.workers) == 1 and calls == []  # UI thread'inde okunmadi
    assert url not in bridge.pdfOutlines

    pool.workers[0].run()
    assert bridge.pdfOutlines[url] == [{"title": "Giris", "level": 0, "page": 0}]
    assert changes

    bridge.loadPdfOutline(url)  # onbellekte: is yok
    assert len(pool.workers) == 1 and len(calls) == 1


def test_load_pdf_outline_missing_file_yields_empty_list(bridge, monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())
    url = (tmp_path / "yok.pdf").as_uri()

    bridge.loadPdfOutline(url)

    assert bridge.pdfOutlines[url] == []


def test_load_pdf_outline_ignores_empty_url(bridge, monkeypatch):
    pool = _RecordingPool()
    monkeypatch.setattr(bridge, "_thread_pool", pool)

    bridge.loadPdfOutline("")

    assert pool.workers == []


def test_delete_resource_drops_cached_outline(bridge, monkeypatch, tmp_path):
    _fake_pdf_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())
    original = tmp_path / "a.pdf"
    original.write_bytes(b"%PDF-1.4 x")
    bridge.importLocalPdf(original.as_uri())
    resource = bridge._controller.load_resources_with_filters({})[0]
    bridge._pdf_outlines[resource.url] = [{"title": "x", "level": 0, "page": 0}]

    bridge.deleteResource(resource.id)

    assert resource.url not in bridge.pdfOutlines


# ---------------------------------------------------------------- library index cache
def test_library_index_is_cached_until_resources_change(bridge, monkeypatch):
    builds = []
    real = bridge._controller.load_resources_with_filters

    def counting(filters):
        builds.append(filters)
        return real(filters)

    monkeypatch.setattr(bridge._controller, "load_resources_with_filters", counting)
    first = bridge._library_index()
    second = bridge._library_index()

    assert first is second
    n_after_two_calls = len(builds)

    bridge._reload_resources()  # kaynaklar degisti -> onbellek gecersiz
    third = bridge._library_index()

    assert third is not first
    assert len(builds) > n_after_two_calls


def test_market_batch_save_reloads_resources_once(bridge, monkeypatch):
    reloads = []
    real_reload = bridge._reload_resources
    monkeypatch.setattr(bridge, "_reload_resources", lambda: (reloads.append(1), real_reload())[1])
    papers = [{"title": f"P{i}", "url": f"https://x.org/{i}", "doi": f"10.1/{i}"} for i in range(4)]

    bridge.saveMarketResults(papers)

    assert bridge.resourcesModel.count == 4
    assert len(reloads) == 1  # 4 kayit icin tek yenileme (olaylar toplu islemde askiya alinir)


def test_events_are_active_again_after_batch(bridge, monkeypatch):
    bridge.saveMarketResults([{"title": "A", "url": "https://x.org/a", "doi": "10.1/a"}])
    reloads = []
    real_reload = bridge._reload_resources
    monkeypatch.setattr(bridge, "_reload_resources", lambda: (reloads.append(1), real_reload())[1])

    bridge._controller.add_resource({"title": "B", "url": "https://x.org/b", "category_id": None, "priority": 2})

    assert reloads  # olay tabanli yenileme yeniden calisiyor
    assert bridge._resource_events_suspended is False
