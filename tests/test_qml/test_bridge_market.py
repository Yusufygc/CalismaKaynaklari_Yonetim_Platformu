"""Makale pazari: arama, sayfalama, kayit, kesif, oneri ve toplu kayit/disa aktarim."""
import pytest

from services.paper_market_service import MarketPage, PaperResult
from tests.test_qml.qml_harness import SyncThreadPool
from ui_qml.bridge import QmlBridge


def test_qml_bridge_search_articles_populates_market_results(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()

    fake_paper = PaperResult(
        title="Attention Is All You Need",
        authors=["Ashish Vaswani"],
        year=2017,
        citation_count=100000,
        url="https://arxiv.org/pdf/1706.03762",
        abstract="Ozet metni.",
    )
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {
            "recent": MarketPage(items=[fake_paper], total=1),
            "popular": MarketPage(),
            "cited": MarketPage(items=[fake_paper], total=1),
        },
    )

    assert bridge.market.marketSearchLoading is False
    bridge.market.searchArticles("transformer")

    assert bridge.market.marketSearchLoading is False
    assert len(bridge.market.marketResults["recent"]) == 1
    assert bridge.market.marketResults["recent"][0]["title"] == "Attention Is All You Need"
    assert bridge.market.marketResults["recent"][0]["citationCount"] == 100000
    assert bridge.market.marketResults["popular"] == []
    assert len(bridge.market.marketResults["cited"]) == 1
    assert bridge.market.marketMeta["recent"]["hasMore"] is False
    assert bridge.market.marketMeta["popular"]["error"] == ""


def _paper(title: str) -> PaperResult:
    return PaperResult(
        title=title, authors=[], year=2020, citation_count=1, url=f"https://x.org/{title}", abstract=None
    )


def test_qml_bridge_market_pagination_appends_and_stops_at_total(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    calls = []

    def fake_search(self, topic, filters=None):
        calls.append(("search", filters))
        return {
            "recent": MarketPage(items=[_paper("a"), _paper("b")], total=3),
            "popular": MarketPage(),
            "cited": MarketPage(),
        }

    def fake_page(self, topic, kind, filters=None, page=1):
        calls.append((kind, page))
        return MarketPage(items=[_paper("c")], total=3)

    monkeypatch.setattr("workers.market_search_worker.PaperMarketService.search", fake_search)
    monkeypatch.setattr("workers.market_search_worker.PaperMarketService.search_page", fake_page)

    bridge.market.searchArticles("gan", {"yearFrom": "2020", "openAccess": True})
    assert bridge.market.marketMeta["recent"]["hasMore"] is True
    assert calls[0][1].year_from == 2020 and calls[0][1].open_access is True

    bridge.market.loadMoreArticles("recent")

    assert [p["title"] for p in bridge.market.marketResults["recent"]] == ["a", "b", "c"]
    assert bridge.market.marketMeta["recent"]["page"] == 2
    assert bridge.market.marketMeta["recent"]["hasMore"] is False
    assert calls[1] == ("recent", 2)

    bridge.market.loadMoreArticles("recent")  # hasMore False -> istek atilmaz
    assert len(calls) == 2


def test_qml_bridge_market_page_error_keeps_existing_results(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {
            "recent": MarketPage(items=[_paper("a")], total=5),
            "popular": MarketPage(),
            "cited": MarketPage(),
        },
    )
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search_page",
        lambda self, topic, kind, filters=None, page=1: MarketPage(error="timeout"),
    )

    bridge.market.searchArticles("gan")
    bridge.market.loadMoreArticles("recent")

    assert len(bridge.market.marketResults["recent"]) == 1
    meta = bridge.market.marketMeta["recent"]
    assert meta["error"] == "timeout" and meta["hasMore"] is True and meta["loadingMore"] is False


def test_qml_bridge_market_search_error_is_distinct_from_empty(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {
            "recent": MarketPage(error="boom"),
            "popular": MarketPage(),
            "cited": MarketPage(),
        },
    )

    bridge.market.searchArticles("gan")

    assert bridge.market.marketMeta["recent"]["error"] == "boom"
    assert bridge.market.marketMeta["popular"]["error"] == ""


def test_qml_bridge_market_ignores_stale_response(qapp, session):
    bridge = QmlBridge(session)
    bridge.market._request_id = 5

    bridge.market._on_search_finished({"recent": MarketPage(items=[_paper("old")], total=1)}, 4)

    assert bridge.market.marketResults["recent"] == []


def test_qml_bridge_market_history_is_deduplicated_and_capped(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {k: MarketPage() for k in ("recent", "popular", "cited")},
    )

    for topic in [f"konu{i}" for i in range(12)] + ["KONU5"]:
        bridge.market.searchArticles(topic)

    history = bridge.market.marketSearchHistory
    assert history[0] == "KONU5" and len(history) == 10
    assert [t.lower() for t in history].count("konu5") == 1

    bridge.market.clearMarketHistory()
    assert bridge.market.marketSearchHistory == []


def test_qml_bridge_search_articles_ignores_blank_topic(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()

    bridge.market.searchArticles("   ")

    assert bridge.market.marketSearchLoading is False
    assert bridge.market.marketResults == {"recent": [], "popular": [], "cited": []}


def test_qml_bridge_save_market_result_creates_resource(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)

    bridge.market.saveMarketResult({
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani"],
        "year": 2017,
        "citationCount": 100000,
        "url": "https://arxiv.org/pdf/1706.03762",
        "abstract": "Ozet metni.",
    })

    assert bridge.library.resourcesModel.rowCount() == 1
    # extra_metadata dogrudan modelde rol olarak yok; controller uzerinden dogrula.
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    assert resource.title == "Attention Is All You Need"
    assert resource.extra_metadata["source"] == "openalex"
    assert resource.extra_metadata["citation_count"] == 100000


def test_qml_bridge_market_results_flag_papers_already_in_library(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    saved = PaperResult(
        title="Kayitli", authors=[], year=2020, citation_count=1, url="https://x.org/k",
        abstract=None, doi="10.1/kayitli",
    )
    fresh = _paper("yeni")
    bridge.market.saveMarketResult(
        {"title": "Kayitli", "url": "https://x.org/k", "doi": "https://doi.org/10.1/KAYITLI"}
    )
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {
            "recent": MarketPage(items=[saved, fresh], total=2),
            "popular": MarketPage(),
            "cited": MarketPage(),
        },
    )

    bridge.market.searchArticles("gan")

    flagged, unflagged = bridge.market.marketResults["recent"]
    assert flagged["libraryResourceId"] > 0
    assert unflagged["libraryResourceId"] == 0


def test_qml_bridge_save_market_result_skips_duplicate_doi(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    notes = []
    bridge.notificationEmitted.connect(lambda kind, msg: notes.append((kind, msg)))
    paper = {"title": "Ayni", "url": "https://x.org/a", "doi": "10.9/ayni"}

    bridge.market.saveMarketResult(paper)
    bridge.market.saveMarketResult(paper)

    assert bridge.library.resourcesModel.count == 1
    assert "zaten" in notes[-1][1]


def test_qml_bridge_saving_a_result_refreshes_library_flag(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    bridge.market._results_cache = {
        "recent": [{"title": "T", "doi": "10.9/t", "openalexId": "", "libraryResourceId": 0}],
        "popular": [],
        "cited": [],
    }
    changes = []
    bridge.market.marketResultsChanged.connect(lambda: changes.append(1))

    bridge.market.saveMarketResult({"title": "T", "url": "https://x.org/t", "doi": "10.9/t"})

    assert bridge.market.marketResults["recent"][0]["libraryResourceId"] > 0
    assert changes


def test_qml_bridge_load_discovery_populates_and_caches(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    calls = []

    def fake_related(self, openalex_id, kind, limit=25):
        calls.append((kind, openalex_id))
        return [_paper("r1")]

    monkeypatch.setattr("workers.related_papers_worker.PaperMarketService.related_papers", fake_related)

    bridge.discovery.loadDiscovery("similar", "W1")
    bridge.discovery.loadDiscovery("similar", "W1")  # onbellekten: ikinci istek yok

    state = bridge.discovery.marketDiscovery["similar:W1"]
    assert state["loaded"] is True and state["loading"] is False
    assert [i["title"] for i in state["items"]] == ["r1"]
    assert calls == [("similar", "W1")]


def test_qml_bridge_load_discovery_reports_error(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()

    def boom(self, openalex_id, kind, limit=25):
        raise RuntimeError("offline")

    monkeypatch.setattr("workers.related_papers_worker.PaperMarketService.related_papers", boom)

    bridge.discovery.loadDiscovery("references", "W1")

    state = bridge.discovery.marketDiscovery["references:W1"]
    assert state["loaded"] is False and state["error"] and state["items"] == []


def test_qml_bridge_search_without_topic_or_author_is_ignored(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()

    bridge.market.searchArticles("", {"yearFrom": "2020"})

    assert bridge.market.marketSearchLoading is False


def test_qml_bridge_reset_market_results_clears_and_invalidates_pending(qapp, session):
    bridge = QmlBridge(session)
    bridge.market._results_cache["recent"] = [{"title": "x"}]
    pending_id = bridge.market._request_id

    bridge.market.resetMarketResults()
    bridge.market._on_search_finished({"recent": MarketPage(items=[_paper("late")], total=1)}, pending_id)

    assert bridge.market.marketResults["recent"] == []


def test_qml_bridge_library_suggestions_use_openalex_ids_of_library(qapp, session, monkeypatch):
    from services.reading_suggestion_service import Suggestion

    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    bridge.market.saveMarketResult({"title": "Kutuphane", "url": "https://x.org/1", "openalexId": "W1"})
    received = []

    def fake_suggest(self, ids, min_frequency=None, limit=20):
        received.append(ids)
        return [Suggestion(_paper("W9"), 2)]

    monkeypatch.setattr("workers.reading_suggestion_worker.ReadingSuggestionService.suggest", fake_suggest)

    bridge.discovery.loadLibrarySuggestions()

    state = bridge.discovery.marketSuggestions
    assert received == [["W1"]]
    assert state["loaded"] is True and state["sourceCount"] == 1
    assert state["items"][0]["citedByLibrary"] == 2


def test_qml_bridge_library_suggestions_without_openalex_sources_skips_network(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()

    bridge.discovery.loadLibrarySuggestions()

    state = bridge.discovery.marketSuggestions
    assert state["sourceCount"] == 0 and state["loading"] is False and state["items"] == []


def _notes(bridge):
    notes = []
    bridge.notificationEmitted.connect(lambda kind, msg: notes.append(msg))
    return notes


def test_qml_bridge_batch_save_adds_new_skips_existing_and_dedups_within_batch(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    notes = _notes(bridge)
    bridge.market.saveMarketResult({"title": "Var", "url": "https://x.org/var", "doi": "10.1/var"})
    notes.clear()

    bridge.market.saveMarketResults([
        {"title": "Var", "url": "https://x.org/var", "doi": "10.1/VAR"},
        {"title": "Yeni", "url": "https://x.org/yeni", "doi": "10.1/yeni"},
        {"title": "Yeni kopya", "url": "https://x.org/yeni2", "doi": "10.1/yeni"},
        {"title": "Baska", "url": "https://x.org/baska", "openalexId": "W5"},
    ])

    assert bridge.library.resourcesModel.count == 3
    assert notes == ["2 makale kaydedildi, 2 tanesi zaten kütüphanendeydi."]


def test_qml_bridge_batch_save_all_duplicates_message(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    paper = {"title": "Var", "url": "https://x.org/var", "doi": "10.1/var"}
    bridge.market.saveMarketResult(paper)
    notes = _notes(bridge)

    bridge.market.saveMarketResults([paper])

    assert notes == ["Seçilen makalelerin hepsi zaten kütüphanende."]


def test_qml_bridge_save_for_later_tags_resource(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)

    bridge.market.saveMarketResultForLater({"title": "Sonra", "url": "https://x.org/s"})

    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    assert "okuma-listesi" in [t.name for t in resource.tags]


def test_qml_bridge_export_market_results_writes_bibtex_and_csv(qapp, session, tmp_path):
    bridge = QmlBridge(session)
    papers = [{"title": "Baslik", "authors": ["Ada Lovelace"], "year": 1843, "doi": "10.1/x", "citationCount": 1}]

    bridge.market.exportMarketResults("bibtex", str(tmp_path / "sonuc"), papers)  # uzanti eklenir
    bridge.market.exportMarketResults("csv", str(tmp_path / "sonuc.csv"), papers)

    assert "@article{lovelace1843baslik" in (tmp_path / "sonuc.bib").read_text(encoding="utf-8")
    raw = (tmp_path / "sonuc.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and b"Baslik" in raw  # Excel icin BOM


def test_qml_bridge_export_market_results_empty_and_invalid(qapp, session, tmp_path):
    bridge = QmlBridge(session)
    notes = _notes(bridge)

    bridge.market.exportMarketResults("csv", str(tmp_path / "x.csv"), [])

    assert notes == ["Dışa aktarılacak sonuç yok."] and not (tmp_path / "x.csv").exists()
    with pytest.raises(ValueError):
        bridge.market.exportMarketResults("pdf", str(tmp_path / "x.pdf"), [{"title": "t"}])
