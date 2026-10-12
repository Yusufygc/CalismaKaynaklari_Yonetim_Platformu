"""Okuma durumu uctan uca (gercek QML): kaldigin yer kaydedilir, okuyucu yeniden acilinca oraya donulur; kartta
ilerleme gorunur.

Geri donus noktasi gorunumun USTUNDEKI sayfa + konumdur (`PdfPageArea.topViewState`); sayfa sayaci (`currentPage`)
gorunumun ortasini gosterir ve yerlesim degisince bir sayfa oynayabilir, bu yuzden testler ust durumu karsilastirir."""
import pytest
from PySide6.QtCore import Q_ARG, Q_RETURN_ARG, QMetaObject, Qt
from PySide6.QtTest import QTest

from tests.pdf_factory import write_outline_pdf
from tests.test_qml.qml_harness import SyncThreadPool, find_named, open_window, pump
from ui_qml.bridge import QmlBridge

PAGES = ["A", "B", "C", "D", "E", "F"]


@pytest.fixture()
def env(qapp, session, tmp_path, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    bridge.library.importLocalPdf(write_outline_pdf(tmp_path / "altı-sayfa.pdf", PAGES).as_uri())
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    engine, window = open_window(qapp, bridge, "showcase", width=1400, height=900)
    yield qapp, bridge, window, resource
    del engine


def _page_area(window):
    return find_named(window, "pageArea")


def _open(qapp, bridge, resource):
    bridge.reader.openReader(resource.id)
    pump(qapp, 150)
    QTest.qWait(900)  # geri yukleme bitip konum kaydi acilir (700 ms yerlesme)
    pump(qapp, 30)


def _top_state(area) -> dict:
    result = QMetaObject.invokeMethod(area, "topViewState", Qt.DirectConnection, Q_RETURN_ARG("QVariant"))
    return result.toVariant()


def _go_to(area, page: int, zoom_in: bool = False) -> None:
    QMetaObject.invokeMethod(area, "goToPage", Qt.DirectConnection, Q_ARG("QVariant", page))
    QTest.qWait(300)  # atlama bitsin; zoom atlamanin ustune binerse sayfa sayaci sifirlanir (kullanici akisi degil)
    if zoom_in:
        QMetaObject.invokeMethod(area, "zoomIn")
    QTest.qWait(700)  # sayfa sayaci (120 ms) ve QML kayit birlestirmesi (500 ms)


def _document_id(bridge, resource) -> int:
    return bridge.ctx.pdf_library.documents().document_for_resource(resource.id).id


def test_reader_returns_to_the_saved_top_position_and_zoom_after_reopening(env):
    qapp, bridge, window, resource = env
    _open(qapp, bridge, resource)
    area = _page_area(window)
    _go_to(area, 2, zoom_in=True)
    before = _top_state(area)
    assert before["page"] >= 1  # sayfa 0 degil: gorunum gercekten ilerledi

    bridge.reader.closeReader()  # kapanista bekleyen kayit yazilir
    pump(qapp, 40)
    state = bridge.ctx.pdf_library.reading().get(_document_id(bridge, resource))
    assert state is not None and state.last_page == before["page"] and state.zoom == pytest.approx(1.2, abs=0.01)
    assert state.loc_y == pytest.approx(max(before["y"], 0), abs=0.5)

    _open(qapp, bridge, resource)
    area = _page_area(window)
    after = _top_state(area)
    assert after["page"] == before["page"]
    assert after["y"] == pytest.approx(before["y"], abs=1.5)
    assert area.property("renderScale") == pytest.approx(1.2, abs=0.01)


def test_first_open_starts_at_the_top_and_does_not_write_a_state_by_itself(env):
    qapp, bridge, window, resource = env

    _open(qapp, bridge, resource)

    assert _page_area(window).property("currentPage") == 0
    assert bridge.ctx.pdf_library.reading().get(_document_id(bridge, resource)) is None


def test_reopening_does_not_overwrite_the_saved_state_with_page_zero(env):
    qapp, bridge, window, resource = env
    _open(qapp, bridge, resource)
    _go_to(_page_area(window), 3)
    saved_page = _top_state(_page_area(window))["page"]
    bridge.reader.closeReader()
    pump(qapp, 40)

    _open(qapp, bridge, resource)
    bridge.reader.closeReader()  # hicbir sey yapmadan kapat
    pump(qapp, 40)

    state = bridge.ctx.pdf_library.reading().get(_document_id(bridge, resource))
    assert saved_page >= 1 and state.last_page == saved_page


def test_library_card_shows_reading_progress_after_the_reader_closes(env):
    qapp, bridge, window, resource = env
    model = bridge.library.resourcesModel
    index = model.index(0, 0)
    role = next(r for r, n in model.roleNames().items() if bytes(n) == b"readingProgress")
    assert model.data(index, role) == 0.0

    _open(qapp, bridge, resource)
    _go_to(_page_area(window), 2)
    bridge.reader.closeReader()
    pump(qapp, 40)

    state = bridge.ctx.pdf_library.reading().get(_document_id(bridge, resource))
    assert state.max_page >= 1
    assert model.data(index, role) == pytest.approx((state.max_page + 1) / len(PAGES))
