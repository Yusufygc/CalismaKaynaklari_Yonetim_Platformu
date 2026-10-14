"""Sayfasi /Rotate ile dondurulmus PDF'lerde (taranmis/yatay belgeler) gercek fareyle secim -> alinti -> vurgu:
Qt koordinatlari goruntulenen (dondurulmus) uzaydadir; secim, saklanan geometri ve tiklama alani ayni yerde olmali."""
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest

from tests.pdf_factory import write_text_pdf
from tests.test_qml.qml_harness import SyncThreadPool, find_named, open_window, pump, reader_document, walk

WORD = "tilki"


@pytest.fixture(params=[90, 180, 270], ids=lambda r: f"rotate{r}")
def view(request, qapp, session, tmp_path, monkeypatch):
    from ui_qml.bridge import QmlBridge

    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "donuk.pdf", rotate=request.param).as_uri())
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    engine, window = open_window(qapp, bridge, "showcase", width=1400, height=900)
    bridge.reader.openReader(resource.id)
    pump(qapp, 150)
    yield qapp, bridge, window, engine, request.param
    del engine


def _page_origin(window, size, render_scale: float) -> tuple[float, float]:
    """Sayfa kagidinin sahnedeki sol ust kosesi: boyutu sayfa*olcek olan gorunur ogenin `mapToScene(0, 0)`'i.
    (Goruntuden beyaz arama, ust cubuk de beyaz oldugundan dikey konumu yanlis verebiliyor.)"""
    wide, high = size.width() * render_scale, size.height() * render_scale
    item = next(
        i for i in walk(window.contentItem())
        if i.isVisible() and abs(i.property("width") - wide) < 1 and abs(i.property("height") - high) < 1
    )
    origin = item.mapToScene(QPointF(0, 0))
    return origin.x(), origin.y()


def _drag(window, start: QPoint, end: QPoint) -> None:
    QTest.mouseMove(window, start)
    QTest.qWait(30)
    QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, start)
    QTest.qWait(30)
    for i in range(1, 11):
        QTest.mouseMove(window, QPoint(start.x() + (end.x() - start.x()) * i // 10, start.y() + (end.y() - start.y()) * i // 10))
        QTest.qWait(30)
    QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, end)
    QTest.qWait(100)


def _word_drag_points(rect, rotation: int, x_left: int, y_top: int, scale: float) -> tuple[QPoint, QPoint]:
    """Kelimenin metin akis yonunde (sayfanin dondurulmus halinde) surukleme baslangic/bitis noktalari; her iki uc
    kelimenin 3 pt dis tarafindadir (kelime bosluklarla cevrili): piksel yuvarlamasi kenar karakteri kacirmasin."""
    cx, cy = rect.x() + rect.width() / 2, rect.y() + rect.height() / 2
    pad = 3
    spans = {
        90: ((cx, rect.top() - pad), (cx, rect.bottom() + pad)),
        180: ((rect.right() + pad, cy), (rect.left() - pad, cy)),
        270: ((cx, rect.bottom() + pad), (cx, rect.top() - pad)),
    }
    (x0, y0), (x1, y1) = spans[rotation]
    return (
        QPoint(int(x_left + x0 * scale), int(y_top + y0 * scale)),
        QPoint(int(x_left + x1 * scale), int(y_top + y1 * scale)),
    )


def test_drag_selection_on_a_rotated_page_saves_the_word_and_places_the_highlight_on_it(view):
    qapp, bridge, window, engine, rotation = view
    doc = reader_document(bridge)
    size = doc.pagePointSize(0)
    assert (size.width(), size.height()) == ((792.0, 612.0) if rotation in (90, 270) else (612.0, 792.0))
    text = doc.getSelectionAtIndex(0, 0, 100000).text()
    start = text.index(WORD)
    rect = doc.getSelectionAtIndex(0, start, len(WORD)).boundingRectangle().normalized()  # Qt: dondurulmuste negatif boyut
    scale = find_named(window, "pageArea").property("renderScale")
    x_left, y_top = _page_origin(window, size, scale)

    _drag(window, *_word_drag_points(rect, rotation, x_left, y_top, scale))
    toolbar = next(i for i in walk(window.contentItem()) if i.objectName() == "newHighlightToolbar" and i.isVisible())
    dot = next(i for i in walk(toolbar) if i.objectName() == "pdfHighlightDot")  # ilk renk (Onemli)
    scene = dot.mapToScene(QPointF(dot.width() / 2, dot.height() / 2))
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(int(scene.x()), int(scene.y())))
    pump(qapp, 40)

    (highlight,) = bridge.ctx.pdf_library.annotations().list_highlights(bridge.pdf.currentDocument["documentId"])
    assert highlight.quote_exact.strip() == WORD and abs(highlight.segments[0].start - start) <= 1
    bounds = bridge.pdf.annotations.data(bridge.pdf.annotations.index(0, 0), bridge.pdf.annotations.BoundingRectRole)
    assert bounds[2] > 0 and bounds[3] > 0, "sinirlayici dikdortgen pozitif boyutlu olmali"
    # Saklanan geometri, kelimenin goruntulenen konumuyla ayni (yarim kelime payi).
    assert abs(bounds[0] - rect.x()) <= rect.width() and abs(bounds[1] - rect.y()) <= rect.height()
    # Tiklama alani gercekten kelimenin ustunde.
    hit = next(i for i in walk(window.contentItem()) if i.objectName() == "highlightHitArea" and i.isVisible())
    center = hit.mapToScene(QPointF(hit.property("width") / 2, hit.property("height") / 2))
    word_center_x = x_left + (rect.x() + rect.width() / 2) * scale
    word_center_y = y_top + (rect.y() + rect.height() / 2) * scale
    assert abs(center.x() - word_center_x) <= rect.width() * scale
    assert abs(center.y() - word_center_y) <= rect.height() * scale
    assert engine.captured_warnings == []
