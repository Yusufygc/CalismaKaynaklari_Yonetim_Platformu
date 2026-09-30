"""Kaynak cekmecesi (InspectorDrawer + alt bilesenleri) gercek fare/klavye ile: pin, favori, durum, not, silme, kapatma."""
import pytest

from tests.test_qml.qml_harness import SyncThreadPool, click, find_item, find_text, focus, open_window, pump, type_text
from ui_qml.bridge import QmlBridge


@pytest.fixture()
def drawer(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    bridge.market.saveMarketResult({"title": "Ornek Kaynak", "url": "https://x.org/a"})
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    bridge.controllers.highlights.create_highlight(resource.id, "ilk alinti", "#EAB308")
    engine, window = open_window(qapp, bridge, "showcase")
    bridge.library.selectResource(resource.id)
    pump(qapp, 40)
    yield qapp, bridge, window, resource
    del engine


def _stored(bridge, resource):
    return bridge.controllers.resources.get_resource(resource.id)


def _tooltip(window, text):
    return find_item(window, lambda i: i.property("tooltip") == text)


def test_pin_and_favorite_buttons_toggle_the_resource(drawer):
    app, bridge, window, resource = drawer

    click(app, window, _tooltip(window, "Sabitle"))
    click(app, window, _tooltip(window, "Favorilere Ekle"))

    stored = _stored(bridge, resource)
    assert stored.is_pinned and stored.is_favorite


def test_status_pill_updates_status(drawer):
    app, bridge, window, resource = drawer

    click(app, window, find_text(window, "Planlandı"))

    assert _stored(bridge, resource).status.value == "PLANNED"


def test_notes_are_saved_from_the_notes_component(drawer):
    app, bridge, window, resource = drawer
    area = find_item(window, lambda i: i.property("placeholderText") == "Markdown notlarını buraya yaz...")
    area.forceActiveFocus()
    pump(app, 5)
    type_text(app, window, "onemli")

    click(app, window, find_text(window, "Notu Kaydet"))

    assert _stored(bridge, resource).content == "onemli"


def test_highlight_summary_lists_the_resource_highlights(drawer):
    _app, _bridge, window, _resource = drawer

    assert find_text(window, "BU KAYNAKTAKİ ALINTILAR (1)") is not None
    assert find_text(window, "“ilk alinti”") is not None


def test_delete_needs_confirmation_and_close_resets_it(drawer):
    app, bridge, window, resource = drawer

    click(app, window, find_text(window, "Sil"))  # 1. tik: onay iste
    assert find_text(window, "Emin misin?") is not None
    click(app, window, _tooltip(window, "Kapat (Esc)"))  # kapatinca onay durumu sifirlanir
    bridge.library.selectResource(resource.id)
    pump(app, 40)
    assert find_text(window, "Emin misin?") is None
    assert _stored(bridge, resource) is not None

    click(app, window, find_text(window, "Sil"))
    click(app, window, find_text(window, "Emin misin?"))
    assert bridge.controllers.resources.get_resource(resource.id) is None
