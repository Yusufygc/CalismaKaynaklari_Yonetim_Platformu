"""QML testleri icin ortak yardimcilar: motor kurulumu, sahne gezme, gercek fare/klavye olaylari."""
import re
import time
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, Qt
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from ui_qml.image_provider import IconImageProvider

QML_DIR = Path(__file__).resolve().parents[2] / "qml"


class SyncThreadPool:
    """QThreadPool yerine worker'i hemen ve senkron calistirir."""

    def start(self, worker) -> None:
        worker.run()


def pump(app, cycles: int = 30) -> None:
    for _ in range(cycles):
        app.processEvents()
        time.sleep(0.005)


def make_engine(bridge) -> QQmlApplicationEngine:
    """Gercek main.qml'i verilen bridge ile yukler; QML uyarilari `engine.captured_warnings`ta toplanir."""
    engine = QQmlApplicationEngine()
    engine.captured_warnings = []
    engine.warnings.connect(lambda ws: engine.captured_warnings.extend(w.toString() for w in ws))
    engine.addImageProvider("icon", IconImageProvider())
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(str(QML_DIR / "main.qml"))
    return engine


def open_window(app, bridge, view: str, width: int = 1300, height: int = 900):
    engine = make_engine(bridge)
    window = engine.rootObjects()[0]
    window.setWidth(width)
    window.setHeight(height)
    bridge.setCurrentView(view)
    pump(app, 40)
    return engine, window


def walk(item):
    yield item
    for child in item.childItems():
        yield from walk(child)


def find_item(window, predicate):
    return next((i for i in walk(window.contentItem()) if i.isVisible() and predicate(i)), None)


def find_text(window, text: str):
    """Gorunen ilk oge: `text` ozelligi tam esit (Text/AppButton vb.)."""
    return find_item(window, lambda i: i.property("text") == text)


def center(item) -> QPoint:
    return item.mapToScene(item.boundingRect().center()).toPoint()


def click(app, window, item) -> None:
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, center(item))
    pump(app, 20)


def type_text(app, window, text: str) -> None:
    keys = {c: getattr(Qt, f"Key_{c.upper()}") for c in "abcdefghijklmnopqrstuvwxyz"}
    for ch in text:
        QTest.keyClick(window, keys[ch])
        pump(app, 2)


def find_named(window, object_name: str):
    """objectName'e gore oge (gorunur agac uzerinden: TableView delegate'leri QObject agacinda degil,
    `findChild` bunlara ulasamaz)."""
    return next((i for i in walk(window.contentItem()) if i.objectName() == object_name), None)


def focus(app, window, object_name: str) -> QObject:
    item = find_named(window, object_name) or window.findChild(QObject, object_name)
    item.forceActiveFocus()
    pump(app, 5)
    return item


_LINE_COMMENT = re.compile(r"//[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def strip_qml_comments(source: str) -> str:
    """Yorumlardaki `bridge.x` gecisleri sozlesme testini yaniltmasin. (Metin icindeki `//`
    -- ornegin URL -- yorum sanilabilir; bridge.<uye> kaliplarini etkilemez.)"""
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", source))


def white_page_box(window) -> tuple[int, int, int]:
    """Goruntude beyaz PDF sayfasinin (sol x, sag x, ust y) piksel konumu."""
    from PySide6.QtGui import QImage

    image = window.grabWindow().convertToFormat(QImage.Format.Format_RGB32)

    def white(x, y):
        c = image.pixelColor(x, y)
        return c.red() > 250 and c.green() > 250 and c.blue() > 250

    xs = [x for x in range(240, image.width(), 2) if white(x, 450)]
    x_left, x_right = xs[0], xs[-1]
    ys = [y for y in range(60, image.height(), 2) if white((x_left + x_right) // 2, y)]
    return x_left, x_right, ys[0]


def drag(app, window, x0: int, x1: int, y: int) -> None:
    from PySide6.QtCore import QPoint

    start, end = QPoint(x0, y), QPoint(x1, y)
    QTest.mouseMove(window, start)
    QTest.qWait(30)
    QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, start)
    QTest.qWait(30)
    for i in range(1, 11):
        QTest.mouseMove(window, QPoint(x0 + (x1 - x0) * i // 10, y))
        QTest.qWait(30)
    QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, end)
    QTest.qWait(100)
