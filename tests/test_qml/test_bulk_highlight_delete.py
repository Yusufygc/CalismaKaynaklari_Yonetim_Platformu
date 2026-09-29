import pytest

from ui_qml.bridge import QmlBridge


@pytest.fixture()
def bridge(qapp, session, monkeypatch):
    b = QmlBridge(session)
    monkeypatch.setattr(b.ctx.extractor, "schedule", lambda *args: None)
    return b


def _resource_with_highlights(bridge, count):
    bridge.market.saveMarketResult({"title": "Kaynak", "url": "https://x.org/a"})
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    for i in range(count):
        bridge.controllers.highlights.create_highlight(resource.id, f"alinti {i}", "#EAB308")
    bridge.reader.reload_highlights()
    return resource


def test_delete_highlights_removes_selected_reloads_once_and_notifies(bridge):
    _resource_with_highlights(bridge, 4)
    ids = [h["id"] for h in bridge.reader.highlights]
    notes, reloads = [], []
    bridge.notificationEmitted.connect(lambda kind, msg: notes.append((kind, msg)))
    bridge.reader.highlightsChanged.connect(lambda: reloads.append(1))

    bridge.reader.deleteHighlights(ids[:3])

    assert [h["id"] for h in bridge.reader.highlights] == [ids[3]]
    assert notes == [("info", "3 alıntı silindi.")]
    assert len(reloads) >= 1


def test_delete_highlights_empty_selection_does_nothing(bridge):
    _resource_with_highlights(bridge, 2)
    notes = []
    bridge.notificationEmitted.connect(lambda kind, msg: notes.append(msg))

    bridge.reader.deleteHighlights([])

    assert len(bridge.reader.highlights) == 2 and notes == []


def test_delete_highlights_refreshes_open_reader(bridge):
    resource = _resource_with_highlights(bridge, 2)
    bridge.reader.openReader(resource.id)
    assert len(bridge.reader.currentReaderResource["highlights"]) == 2

    bridge.reader.deleteHighlights([h["id"] for h in bridge.reader.highlights])

    assert bridge.reader.currentReaderResource["highlights"] == []
