from datetime import timedelta

import pytest

from services.paper_market_service import MarketPage, PaperResult
from ui_qml.bridge import QmlBridge


class _SyncThreadPool:
    def start(self, worker) -> None:
        worker.run()


def _paper(openalex_id: str) -> PaperResult:
    return PaperResult(
        title=f"P {openalex_id}", authors=[], year=2024, citation_count=0,
        url=f"https://x.org/{openalex_id}", abstract=None, openalex_id=openalex_id,
    )


def _stub_search(monkeypatch, ids=("a", "b")):
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {
            "recent": MarketPage(items=[_paper(i) for i in ids], total=len(ids)),
            "popular": MarketPage(),
            "cited": MarketPage(),
        },
    )


@pytest.fixture()
def bridge(qapp, session, monkeypatch):
    b = QmlBridge(session)
    b.ctx.thread_pool = _SyncThreadPool()
    monkeypatch.setattr(b.ctx.extractor, "schedule", lambda *args: None)
    return b


def _collect_notes(bridge):
    notes = []
    bridge.notificationEmitted.connect(lambda kind, msg: notes.append((kind, msg)))
    return notes


def test_save_search_marks_current_results_as_seen(bridge, monkeypatch):
    _stub_search(monkeypatch)
    notes = _collect_notes(bridge)
    bridge.market.searchArticles("gan")

    bridge.searches.saveSearch("gan", {"yearFrom": "2020", "authorName": ""}, "tez")

    saved = bridge.searches.savedSearches
    assert len(saved) == 1
    assert saved[0]["label"] == "gan" and saved[0]["tag"] == "tez" and saved[0]["newCount"] == 0
    assert saved[0]["filters"] == {"yearFrom": "2020"}
    assert bridge.controllers.saved_searches.load_saved_searches()[0].seen_ids == ["a", "b"]
    assert notes[-1] == ("info", "Arama kaydedildi: gan")
    assert bridge.searches.activeSavedSearchId == saved[0]["id"]


def test_save_search_duplicate_shows_error(bridge, monkeypatch):
    _stub_search(monkeypatch)
    bridge.market.searchArticles("gan")
    bridge.searches.saveSearch("gan", {}, "")
    notes = _collect_notes(bridge)

    bridge.searches.saveSearch("GAN", {}, "")

    assert len(bridge.searches.savedSearches) == 1
    assert notes[-1] == ("error", "Bu arama zaten kayitli.")


def _saved_resource_tag_names(bridge, title):
    resource = next(r for r in bridge.controllers.resources.load_resources_with_filters({}) if r.title == title)
    return [t.name for t in resource.tags]


@pytest.fixture()
def pending_saved_search(bridge, monkeypatch):
    """'gan' aramasi 'tez' etiketiyle kayitli ve 3 yeni sonucu bekliyor; (bridge, arama_id) dondurur."""
    _stub_search(monkeypatch, ("a",))
    bridge.market.searchArticles("gan")
    bridge.searches.saveSearch("gan", {"openAccess": True}, "tez")
    search_id = bridge.searches.savedSearches[0]["id"]
    bridge.controllers.saved_searches.record_saved_search_check(search_id, 3)
    assert bridge.searches.savedSearches[0]["newCount"] == 3
    _stub_search(monkeypatch, ("a", "b", "c"))
    return bridge, search_id


def test_run_saved_search_applies_form_and_marks_seen(pending_saved_search):
    bridge, search_id = pending_saved_search
    applied = []
    bridge.searches.savedSearchApplied.connect(lambda topic, filters: applied.append((topic, dict(filters))))

    bridge.searches.runSavedSearch(search_id)

    assert applied == [("gan", {"openAccess": True})]
    assert bridge.searches.activeSavedSearchId == search_id
    assert bridge.searches.savedSearches[0]["newCount"] == 0
    assert bridge.controllers.saved_searches.load_saved_searches()[0].seen_ids == ["a", "b", "c"]


def test_saving_result_during_saved_search_adds_its_tag(pending_saved_search):
    bridge, search_id = pending_saved_search
    bridge.searches.runSavedSearch(search_id)

    bridge.market.saveMarketResult({"title": "Kayit", "url": "https://x.org/k"})

    assert "tez" in _saved_resource_tag_names(bridge, "Kayit")


def test_manual_search_drops_saved_search_context_and_tag(pending_saved_search):
    bridge, search_id = pending_saved_search
    bridge.searches.runSavedSearch(search_id)

    bridge.market.searchArticles("baska")  # elle yeni arama: kayitli arama baglami birakilir
    assert bridge.searches.activeSavedSearchId == 0
    bridge.market.saveMarketResult({"title": "Kayit2", "url": "https://y.org/k"})

    assert "tez" not in _saved_resource_tag_names(bridge, "Kayit2")


def test_delete_saved_search_clears_active(bridge, monkeypatch):
    _stub_search(monkeypatch)
    bridge.market.searchArticles("gan")
    bridge.searches.saveSearch("gan", {}, "")
    search_id = bridge.searches.savedSearches[0]["id"]
    bridge.searches.runSavedSearch(search_id)
    assert bridge.searches.activeSavedSearchId == search_id

    bridge.searches.deleteSavedSearch(search_id)

    assert bridge.searches.savedSearches == [] and bridge.searches.activeSavedSearchId == 0


def test_reset_market_results_clears_active_saved_search(bridge, monkeypatch):
    _stub_search(monkeypatch)
    bridge.market.searchArticles("gan")
    bridge.searches.saveSearch("gan", {}, "")
    bridge.searches.runSavedSearch(bridge.searches.savedSearches[0]["id"])

    bridge.market.resetMarketResults()

    assert bridge.searches.activeSavedSearchId == 0


def test_check_saved_searches_records_new_counts_and_retries_failures(bridge, session, monkeypatch):
    ok = bridge.controllers.saved_searches.create_saved_search("ok", {}, None, ["W1"])
    bad = bridge.controllers.saved_searches.create_saved_search("bad", {}, None, [])
    for search in (ok, bad):
        search.last_checked_at = None  # hic kontrol edilmemis -> vadesi gelmis
    session.commit()
    pages = {
        "ok": MarketPage(items=[_paper("W1"), _paper("W2"), _paper("W3")], total=3),
        "bad": MarketPage(error="offline"),
    }
    monkeypatch.setattr(
        "workers.saved_search_worker.PaperMarketService.search_page",
        lambda self, topic, kind, filters=None, page=1: pages[topic],
    )

    bridge.searches.checkSavedSearches()

    by_topic = {s["topic"]: s for s in bridge.searches.savedSearches}
    assert by_topic["ok"]["newCount"] == 2
    assert by_topic["bad"]["newCount"] == 0
    # Basarisiz kontrol "son kontrol"u guncellemez: bir sonraki acilista yeniden denenir.
    due_topics = {s.topic for s in bridge.controllers.saved_searches.load_due_saved_searches(timedelta(hours=1))}
    assert due_topics == {"bad"}
    assert bridge.searches._checking is False


def test_check_saved_searches_skips_when_none_due(bridge, monkeypatch):
    bridge.controllers.saved_searches.create_saved_search("fresh", {}, None, [])  # az once olusturuldu -> vadesi gelmedi
    called = []
    monkeypatch.setattr(
        "workers.saved_search_worker.PaperMarketService.search_page",
        lambda *args, **kwargs: called.append(1),
    )

    bridge.searches.checkSavedSearches()

    assert called == []


def test_check_saved_searches_skips_the_active_one(bridge, session, monkeypatch):
    _stub_search(monkeypatch)
    search = bridge.controllers.saved_searches.create_saved_search("gan", {}, None, [])
    search.last_checked_at = None
    session.commit()
    bridge.searches.reload_saved_searches()
    bridge.searches.runSavedSearch(search.id)
    called = []
    monkeypatch.setattr(
        "workers.saved_search_worker.PaperMarketService.search_page",
        lambda *args, **kwargs: called.append(1),
    )
    search.last_checked_at = None
    session.commit()

    bridge.searches.checkSavedSearches()

    assert called == []
