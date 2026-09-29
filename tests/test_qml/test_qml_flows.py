"""Gercek QML + gercek fare/klavye olaylariyla uctan uca akislar (offscreen).

Onceki hatalarin regresyon testleri: 'Tekrar dene' tiklamasini ust uste binen liste yutuyordu;
Bilgi Havuzu toplu silme ve kayitli arama akislari.
"""
import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest

from services.paper_market_service import MarketPage, PaperResult
from tests.test_qml.qml_harness import (
    SyncThreadPool,
    click,
    find_item,
    find_text,
    focus,
    open_window,
    pump,
    type_text,
)
from ui_qml.bridge import QmlBridge


def _paper(n: int) -> PaperResult:
    return PaperResult(
        title=f"Makale {n}", authors=["Ada"], year=2024, citation_count=n, url=f"https://x.org/{n}",
        abstract="Ozet", doi=f"10.1/{n}", openalex_id=f"W{n}", author_ids=["A1"],
    )


@pytest.fixture()
def bridge(qapp, session, monkeypatch):
    b = QmlBridge(session)
    monkeypatch.setattr(b, "_thread_pool", SyncThreadPool())
    monkeypatch.setattr(b, "_schedule_full_text_extract", lambda *args: None)
    return b


def _search_and_enter(app, window, text: str) -> None:
    focus(app, window, "topicInput")
    type_text(app, window, text)
    QTest.keyClick(window, Qt.Key_Return)
    pump(app, 30)


def test_market_retry_button_is_clickable_and_searches_again(qapp, bridge, monkeypatch):
    state = {"fail": True, "calls": 0}

    def fake_search(self, topic, filters=None):
        state["calls"] += 1
        if state["fail"]:
            return {kind: MarketPage(error="offline") for kind in ("recent", "popular", "cited")}
        return {"recent": MarketPage([_paper(1)], 1), "popular": MarketPage(), "cited": MarketPage()}

    monkeypatch.setattr("workers.market_search_worker.PaperMarketService.search", fake_search)
    engine, window = open_window(qapp, bridge, "articleMarket")

    _search_and_enter(qapp, window, "gan")
    assert state["calls"] == 1 and bridge.marketMeta["recent"]["error"] == "offline"

    state["fail"] = False
    retry = find_text(window, "Tekrar dene")
    assert retry is not None, "hata durumunda 'Tekrar dene' gorunmeli"
    click(qapp, window, retry)

    assert state["calls"] == 2  # tiklama listeye degil butona ulasti (eski hata: z-order)
    assert len(bridge.marketResults["recent"]) == 1
    assert engine.captured_warnings == []
    del engine


def test_market_bulk_selection_and_save_by_real_clicks(qapp, bridge, monkeypatch):
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {
            "recent": MarketPage([_paper(1), _paper(2), _paper(3)], 3),
            "popular": MarketPage(), "cited": MarketPage(),
        },
    )
    engine, window = open_window(qapp, bridge, "articleMarket")
    _search_and_enter(qapp, window, "gan")
    view = window.findChild(QObject, "articleMarketView")

    assert view.property("selectionCount") == 0

    click(qapp, window, find_text(window, "Tümünü seç"))
    assert view.property("selectionCount") == 3

    click(qapp, window, find_text(window, "Seçilenleri Kaydet (3)"))

    assert bridge.resourcesModel.count == 3
    assert view.property("selectionCount") == 0
    del engine


def _walk_visible(window):
    from tests.test_qml.qml_harness import walk
    return [i for i in walk(window.contentItem()) if i.isVisible()]


def test_saved_search_flow_save_badge_run_and_delete(qapp, bridge, monkeypatch):
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {
            "recent": MarketPage([_paper(1), _paper(2)], 2), "popular": MarketPage(), "cited": MarketPage(),
        },
    )
    engine, window = open_window(qapp, bridge, "articleMarket")
    _search_and_enter(qapp, window, "gan")

    click(qapp, window, find_text(window, "Aramayı kaydet"))
    type_text(qapp, window, "tez")
    QTest.keyClick(window, Qt.Key_Return)  # popup onAccepted -> Kaydet
    pump(qapp, 30)

    assert [(s["label"], s["tag"]) for s in bridge.savedSearches] == [("gan", "tez")]
    assert bridge.activeSavedSearchId == bridge.savedSearches[0]["id"]
    assert find_text(window, "Aramayı kaydet") is None  # zaten kayitli: buton gizlendi

    bridge._controller.record_saved_search_check(bridge.savedSearches[0]["id"], 2)  # yeni yayin var
    pump(qapp, 10)
    chip = find_item(window, lambda i: i.property("text") == "gan  ·  2 yeni")
    assert chip is not None, "yeni yayin rozeti cipte gorunmeli"

    delete_button = find_item(window, lambda i: i.property("tooltip") == "Kayıtlı aramayı sil")
    click(qapp, window, delete_button)

    assert bridge.savedSearches == [] and bridge.activeSavedSearchId == 0
    del engine


def test_knowledge_pool_bulk_delete_with_confirmation(qapp, bridge):
    bridge.saveMarketResult({"title": "Kaynak", "url": "https://x.org/a"})
    resource = bridge._controller.load_resources_with_filters({})[0]
    for i in range(4):
        bridge._controller.create_highlight(resource.id, f"alinti {i}", "#EAB308")
    bridge.reload_highlights()
    engine, window = open_window(qapp, bridge, "knowledge")
    view = find_item(window, lambda i: i.property("selectedCount") is not None)

    checkboxes = [i for i in _walk_visible(window) if i.property("checked") is not None]
    assert len(checkboxes) == 4
    click(qapp, window, checkboxes[0])
    click(qapp, window, checkboxes[1])
    assert view.property("selectedCount") == 2

    click(qapp, window, find_text(window, "Seçilenleri Sil (2)"))
    click(qapp, window, find_text(window, "Vazgeç"))  # onay penceresi: vazgec
    assert len(bridge.highlights) == 4

    click(qapp, window, find_text(window, "Seçilenleri Sil (2)"))
    click(qapp, window, find_text(window, "Sil (2)"))

    assert len(bridge.highlights) == 2
    assert view.property("selectedCount") == 0
    assert engine.captured_warnings == []
    del engine


def test_knowledge_pool_search_is_turkish_insensitive(qapp, bridge):
    bridge.saveMarketResult({"title": "Kaynak", "url": "https://x.org/a"})
    resource = bridge._controller.load_resources_with_filters({})[0]
    for content in ("İstanbul'un tarihi", "Isparta gülleri", "Şeker üretimi"):
        bridge._controller.create_highlight(resource.id, content, "#EAB308")
    bridge.reload_highlights()
    engine, window = open_window(qapp, bridge, "knowledge")
    view = find_item(window, lambda i: i.property("selectedCount") is not None)

    def visible_cards(query: str) -> int:
        view.setProperty("searchQuery", query)
        pump(qapp, 10)
        return len([i for i in _walk_visible(window) if i.property("checked") is not None])

    from utils.text_utils import fold_tr
    assert visible_cards(fold_tr("ISTANBUL")) == 1
    assert visible_cards(fold_tr("ısparta")) == 1
    assert visible_cards(fold_tr("seker")) == 1
    assert visible_cards("yok boyle bir sey") == 0
    del engine
