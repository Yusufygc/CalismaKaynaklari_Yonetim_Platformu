"""Ayarlar sayfasi: kategori/etiket satir ici duzenleme ve onayli silme (gercek fare/klavye, offscreen)."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from tests.test_qml.qml_harness import SyncThreadPool, click, find_item, focus, open_window, pump, type_text
from ui_qml.bridge import QmlBridge


@pytest.fixture()
def bridge(qapp, session, monkeypatch):
    b = QmlBridge(session)
    b.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(b.ctx.extractor, "schedule", lambda *args: None)
    return b


def _named(window, name):
    return find_item(window, lambda i: i.objectName() == name)


def _select_all_and_type(app, window, field_name, text):
    field = focus(app, window, field_name)
    field.selectAll()
    QTest.keyClick(window, Qt.Key_Delete)
    type_text(app, window, text)


def _notes(bridge):
    notes = []
    bridge.notificationEmitted.connect(lambda kind, msg: notes.append((kind, msg)))
    return notes


def test_category_rename_and_recolor_by_real_clicks(qapp, bridge):
    bridge.settings.createCategory("Kitap", "#64748B", "")
    engine, window = open_window(qapp, bridge, "settings")

    click(qapp, window, _named(window, "categoryEditButton"))
    _select_all_and_type(qapp, window, "categoryNameEdit", "roman")
    swatches = _all(window, "colorSwatch")
    edit_palette = swatches[len(swatches) // 2 :]  # ilk yarisi "Yeni Kategori" paleti, ikinci yarisi satirin paleti
    target = next(s for s in edit_palette if s.property("color").name().lower() != "#64748b")
    target_hex = target.property("color").name().lower()
    click(qapp, window, target)
    click(qapp, window, _named(window, "categorySaveButton"))

    category = bridge.settings.categories[0]
    assert category["name"] == "roman"
    assert category["color_hex"].lower() == target_hex
    assert _named(window, "categoryNameEdit") is None  # gorunum moduna dondu
    assert _named(window, "categoryNameText").property("text") == "roman"


def test_category_duplicate_name_keeps_edit_open_and_shows_error(qapp, bridge):
    bridge.settings.createCategory("kitap", "#64748B", "")
    bridge.settings.createCategory("makale", "#64748B", "")
    notes = _notes(bridge)
    engine, window = open_window(qapp, bridge, "settings")

    edit_buttons = _all(window, "categoryEditButton")
    click(qapp, window, edit_buttons[0])
    _select_all_and_type(qapp, window, "categoryNameEdit", "makale")
    QTest.keyClick(window, Qt.Key_Return)
    pump(qapp, 20)

    assert _named(window, "categoryNameEdit") is not None  # duzenleme acik
    assert any(kind == "error" for kind, _ in notes)
    assert sorted(c["name"] for c in bridge.settings.categories) == ["kitap", "makale"]


def test_category_escape_cancels_without_saving(qapp, bridge):
    bridge.settings.createCategory("Kitap", "#64748B", "")
    engine, window = open_window(qapp, bridge, "settings")

    click(qapp, window, _named(window, "categoryEditButton"))
    _select_all_and_type(qapp, window, "categoryNameEdit", "baska")
    QTest.keyClick(window, Qt.Key_Escape)
    pump(qapp, 20)

    assert _named(window, "categoryNameEdit") is None
    assert bridge.settings.categories[0]["name"] == "Kitap"


def test_tag_rename_by_enter_and_duplicate_rejected(qapp, bridge):
    bridge.settings.createTag("ai")
    bridge.settings.createTag("ml")
    notes = _notes(bridge)
    engine, window = open_window(qapp, bridge, "settings")
    click(qapp, window, _tab_tags(window))  # Etiketler sekmesi
    pump(qapp, 10)

    click(qapp, window, _all(window, "tagEditButton")[0])
    _select_all_and_type(qapp, window, "tagNameEdit", "ml")
    QTest.keyClick(window, Qt.Key_Return)
    pump(qapp, 20)
    assert _named(window, "tagNameEdit") is not None
    assert any(kind == "error" for kind, _ in notes)

    _select_all_and_type(qapp, window, "tagNameEdit", "yz")
    QTest.keyClick(window, Qt.Key_Return)
    pump(qapp, 20)
    assert sorted(t["name"] for t in bridge.settings.tags) == ["ml", "yz"]
    assert _named(window, "tagNameEdit") is None


def test_delete_asks_confirmation_cancel_keeps_confirm_removes(qapp, bridge):
    bridge.settings.createCategory("Kitap", "#64748B", "")
    engine, window = open_window(qapp, bridge, "settings")

    click(qapp, window, _named(window, "categoryDeleteButton"))
    click(qapp, window, _named(window, "confirmCancelButton"))
    assert len(bridge.settings.categories) == 1

    click(qapp, window, _named(window, "categoryDeleteButton"))
    click(qapp, window, _named(window, "confirmAcceptButton"))
    assert bridge.settings.categories == []


def _all(window, name):
    from tests.test_qml.qml_harness import walk

    return [i for i in walk(window.contentItem()) if i.isVisible() and i.objectName() == name]


def _tab_tags(window):
    from tests.test_qml.qml_harness import find_text

    return find_text(window, "Etiketler")
