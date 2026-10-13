"""Kullanim Kilavuzu: kenar cubugundan acilir, bolumler/gorseller yuklenir, icindekiler kaydirir; metin teknik terim icermez."""
import re
from pathlib import Path

from PySide6.QtTest import QTest

from tests.test_qml.qml_harness import click, find_item, find_named, open_window, pump, walk
from ui_qml.bridge import QmlBridge

ROOT = Path(__file__).resolve().parents[2]
GUIDE_JS = ROOT / "qml" / "js" / "guide.js"
IMAGES = ROOT / "assets" / "guide"

# Son kullanicinin anlamayacagi (kod/altyapi) terimler: kilavuz metninde GECMEZ. Arayuzde gorunen dugme adlari serbesttir.
TECHNICAL_TERMS = [
    "FTS", "vault", "citekey", "sentinel", "SQLite", "OCR", "API", "WAL", "thread", "OpenAlex", "pkm://", "regex",
    "migration", "alembic", "cache", "debounce", "token", "index", "dizinle", "veritabanı", "veritabani", "sunucu", "bridge",
]


def _guide_text() -> str:
    return GUIDE_JS.read_text(encoding="utf-8")


def _visible(window, name):
    return [i for i in walk(window.contentItem()) if i.objectName() == name and i.isVisible()]


def test_the_guide_text_has_no_technical_jargon():
    text = _guide_text()
    lowered = text.lower()
    found = [term for term in TECHNICAL_TERMS if term.lower() in lowered]
    assert found == [], f"kilavuz metninde teknik terim var: {found}"


def test_every_section_has_the_expected_fields_and_every_image_exists_on_disk():
    text = _guide_text()
    ids = re.findall(r'^\s+id: "([^"]+)"', text, flags=re.M)
    assert len(ids) >= 10 and len(ids) == len(set(ids))
    images = re.findall(r'image: "([^"]*)"', text)
    assert len(images) == len(ids)  # her bolum `image` alani tasir (bos olabilir)
    used = [name for name in images if name]
    assert len(used) >= 8
    missing = [name for name in used if not (IMAGES / name).is_file()]
    assert missing == [], f"eksik gorsel: {missing}"
    assert all((IMAGES / name).stat().st_size > 5_000 for name in used)  # bos/bozuk dosya degil


def test_the_sidebar_has_a_guide_item_that_opens_the_guide(qapp, session):
    bridge = QmlBridge(session)
    engine, window = open_window(qapp, bridge, "showcase", width=1280, height=800)
    item = find_item(window, lambda i: i.property("title") == "Kullanım Kılavuzu")
    assert item is not None and not item.property("isActive")

    click(qapp, window, item)
    pump(qapp, 20)

    assert bridge.currentView == "guide" and item.property("isActive")
    assert len(_visible(window, "guideSection")) >= 1
    assert engine.captured_warnings == []  # eksik gorsel ya da baglama uyarisi yok


def test_all_sections_render_with_steps_images_and_tips_without_warnings(qapp, session):
    bridge = QmlBridge(session)
    engine, window = open_window(qapp, bridge, "guide", width=1280, height=800)
    pump(qapp, 30)
    sections = [i for i in walk(window.contentItem()) if i.objectName() == "guideSection"]
    expected = len(re.findall(r'^\s+id: "', _guide_text(), flags=re.M))
    assert len(sections) == expected
    assert len([i for i in walk(window.contentItem()) if i.objectName() == "guideStep"]) >= expected * 2
    QTest.qWait(300)  # gorseller asenkron yuklenir
    pump(qapp, 20)
    images = _visible(window, "guideImage")  # gorseli olmayan bolumlerin gorsel alani gizlidir
    assert len(images) == len(re.findall(r'image: "[^"]+"', _guide_text())) and all(img.property("progress") == 1.0 and img.property("paintedWidth") > 0 for img in images)  # yuklendi
    assert engine.captured_warnings == []


def test_the_table_of_contents_scrolls_to_the_chosen_section_and_follows_scrolling(qapp, session):
    bridge = QmlBridge(session)
    engine, window = open_window(qapp, bridge, "guide", width=1280, height=800)
    pump(qapp, 30)
    flick = find_named(window, "guideFlick")
    items = _visible(window, "guideTocItem")
    assert len(items) >= 8 and flick.property("contentY") == 0

    click(qapp, window, items[4])  # 5. bolum
    QTest.qWait(600)
    pump(qapp, 10)
    assert flick.property("contentY") > 500
    view = find_item(window, lambda i: i.property("currentIndex") is not None and i.property("sections") is not None)
    assert view.property("currentIndex") == 4

    flick.setProperty("contentY", 0)  # elle yukari kaydirinca vurgu ilk bolume doner
    pump(qapp, 10)
    assert view.property("currentIndex") == 0 and engine.captured_warnings == []
