from pathlib import Path

import pytest

from ui_qml.bridge import QmlBridge
from services.paper_market_service import MarketPage, PaperResult


@pytest.fixture(autouse=True)
def _no_real_pdf_downloads(monkeypatch):
    """Web-PDF'i acan testler gercek ag istegi atmasin (indirme bridge testlerinde
    ayrica, sahte worker ile test ediliyor)."""
    monkeypatch.setattr(QmlBridge, "_start_pdf_download", lambda self, resource: None)


def test_qml_bridge_initial_state(qapp, session):
    bridge = QmlBridge(session)

    assert bridge.isDarkTheme is True
    assert bridge.isSimpleMode is False
    assert bridge.currentView == "showcase"
    assert bridge.isDrawerOpen is False
    assert bridge.selectedResource == {}
    assert bridge.resourcesModel is not None
    assert isinstance(bridge.categories, list)
    assert isinstance(bridge.tags, list)
    assert isinstance(bridge.highlights, list)
    assert isinstance(bridge.vocabulary, list)
    assert "total" in bridge.stats


def test_qml_bridge_theme_and_view_toggle(qapp, session):
    bridge = QmlBridge(session)

    # Tema değiştirme
    bridge.toggleTheme()
    assert bridge.isDarkTheme is False
    bridge.toggleTheme()
    assert bridge.isDarkTheme is True

    # Görünüm değiştirme
    bridge.setCurrentView("knowledge")
    assert bridge.currentView == "knowledge"
    bridge.setCurrentView("settings")
    assert bridge.currentView == "settings"

    # Sade mod (isSimpleMode) değiştirme
    simple_changes = []
    bridge.isSimpleModeChanged.connect(lambda val: simple_changes.append(val))
    assert bridge.isSimpleMode is False

    bridge.setSimpleMode(True)
    assert bridge.isSimpleMode is True
    assert simple_changes == [True]

    bridge.setSimpleMode(True)  # Değişiklik yoksa tekrar sinyal fırlatmamalı
    assert len(simple_changes) == 1

    bridge.setSimpleMode(False)
    assert bridge.isSimpleMode is False
    assert simple_changes == [True, False]


def test_qml_bridge_resource_crud_and_drawer(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_scrape", lambda *args: None)

    # 1. Yeni kaynak ekleme
    bridge.saveResource({
        "title": "QML Kaynağı",
        "url": "https://example.com/qml",
        "status": "PLANNED",
        "priority": 3,
        "content": "Notlar",
    })

    assert bridge.resourcesModel.rowCount() >= 1
    res_id = bridge.selectedResource.get("id")
    assert res_id is not None
    assert bridge.isDrawerOpen is True
    assert bridge.selectedResource["title"] == "QML Kaynağı"

    # 2. Pin ve Favori
    bridge.togglePin(res_id)
    assert bridge.selectedResource["isPinned"] is True

    bridge.toggleFavorite(res_id)
    assert bridge.selectedResource["isFavorite"] is True

    # 3. Durum ve Not Güncelleme
    bridge.updateResourceStatus(res_id, "COMPLETED")
    assert bridge.selectedResource["status"] == "COMPLETED"

    bridge.updateResourceNotes(res_id, "Yeni Notlar")
    assert bridge.selectedResource["content"] == "Yeni Notlar"

    # 4. Çekmeceyi kapatma
    bridge.closeDrawer()
    assert bridge.isDrawerOpen is False

    # 5. Silme
    bridge.deleteResource(res_id)
    assert bridge.resourcesModel.rowCount() == 0


def test_qml_bridge_categories_and_tags(qapp, session):
    bridge = QmlBridge(session)

    # Kategori
    bridge.createCategory("Teknoloji", "#6366F1", "fa5s.laptop")
    assert len(bridge.categories) == 1
    cat_id = bridge.categories[0]["id"]
    assert bridge.categories[0]["name"] == "Teknoloji"

    # Etiket
    bridge.createTag("python")
    assert len(bridge.tags) == 1
    tag_id = bridge.tags[0]["id"]
    assert bridge.tags[0]["name"] == "python"

    # Silme
    bridge.deleteCategory(cat_id)
    assert len(bridge.categories) == 0

    bridge.deleteTag(tag_id)
    assert len(bridge.tags) == 0


def test_qml_bridge_highlights_and_vocabulary(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_scrape", lambda *args: None)

    bridge.saveResource({"title": "Okuma Makalesi", "url": "https://example.com/article"})
    res_id = bridge.selectedResource["id"]

    # Alıntı ekleme
    bridge.addHighlight(res_id, "Onemli bir cumle", "#EAB308")
    assert len(bridge.highlights) == 1
    assert bridge.highlights[0]["content"] == "Onemli bir cumle"

    # Kelime ekleme
    bridge.addVocabulary(res_id, "ubiquitous", "her yerde bulunan", "It is ubiquitous.")
    assert len(bridge.vocabulary) == 1
    assert bridge.vocabulary[0]["word"] == "ubiquitous"

    # Silme
    bridge.deleteHighlight(bridge.highlights[0]["id"])
    assert len(bridge.highlights) == 0


def test_qml_bridge_add_highlight_with_pdf_position(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)

    bridge.saveMarketResult({
        "title": "PDF Kaynak", "authors": [], "year": None, "citationCount": 0,
        "url": "https://example.com/x.pdf", "abstract": "",
    })
    res_id = bridge._controller.load_resources_with_filters({})[0].id

    bridge.addHighlight(res_id, "sayfa alintisi", "#EAB308", 2, 100, 30)

    hl = bridge._controller.load_resource_highlights(res_id)[0]
    assert hl.page_number == 2
    assert hl.start_index == 100
    assert hl.length == 30

    # currentReaderResource serialize edilirken de dogru donmeli
    bridge.openReader(res_id)
    serialized = bridge.currentReaderResource["highlights"][0]
    assert serialized["page"] == 2
    assert serialized["startIndex"] == 100
    assert serialized["length"] == 30


def test_qml_bridge_update_highlight_color(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_scrape", lambda *args: None)

    bridge.saveResource({"title": "Renk Testi", "url": "https://example.com/renk"})
    res_id = bridge.selectedResource["id"]
    bridge.addHighlight(res_id, "renk degisecek", "#EAB308")
    highlight_id = bridge.highlights[0]["id"]

    bridge.updateHighlightColor(highlight_id, "#22C55E")

    assert bridge.highlights[0]["color"] == "#22C55E"


class _SyncThreadPool:
    """QThreadPool yerine worker'i hemen ve senkron calistiran test yardimcisi."""

    def start(self, worker) -> None:
        worker.run()


def test_qml_bridge_search_articles_populates_market_results(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())

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

    assert bridge.marketSearchLoading is False
    bridge.searchArticles("transformer")

    assert bridge.marketSearchLoading is False
    assert len(bridge.marketResults["recent"]) == 1
    assert bridge.marketResults["recent"][0]["title"] == "Attention Is All You Need"
    assert bridge.marketResults["recent"][0]["citationCount"] == 100000
    assert bridge.marketResults["popular"] == []
    assert len(bridge.marketResults["cited"]) == 1
    assert bridge.marketMeta["recent"]["hasMore"] is False
    assert bridge.marketMeta["popular"]["error"] == ""


def _paper(title: str) -> PaperResult:
    return PaperResult(
        title=title, authors=[], year=2020, citation_count=1, url=f"https://x.org/{title}", abstract=None
    )


def test_qml_bridge_market_pagination_appends_and_stops_at_total(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())
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

    bridge.searchArticles("gan", {"yearFrom": "2020", "openAccess": True})
    assert bridge.marketMeta["recent"]["hasMore"] is True
    assert calls[0][1].year_from == 2020 and calls[0][1].open_access is True

    bridge.loadMoreArticles("recent")

    assert [p["title"] for p in bridge.marketResults["recent"]] == ["a", "b", "c"]
    assert bridge.marketMeta["recent"]["page"] == 2
    assert bridge.marketMeta["recent"]["hasMore"] is False
    assert calls[1] == ("recent", 2)

    bridge.loadMoreArticles("recent")  # hasMore False -> istek atilmaz
    assert len(calls) == 2


def test_qml_bridge_market_page_error_keeps_existing_results(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())
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

    bridge.searchArticles("gan")
    bridge.loadMoreArticles("recent")

    assert len(bridge.marketResults["recent"]) == 1
    meta = bridge.marketMeta["recent"]
    assert meta["error"] == "timeout" and meta["hasMore"] is True and meta["loadingMore"] is False


def test_qml_bridge_market_search_error_is_distinct_from_empty(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {
            "recent": MarketPage(error="boom"),
            "popular": MarketPage(),
            "cited": MarketPage(),
        },
    )

    bridge.searchArticles("gan")

    assert bridge.marketMeta["recent"]["error"] == "boom"
    assert bridge.marketMeta["popular"]["error"] == ""


def test_qml_bridge_market_ignores_stale_response(qapp, session):
    bridge = QmlBridge(session)
    bridge._market_request_id = 5

    bridge._on_market_search_finished({"recent": MarketPage(items=[_paper("old")], total=1)}, 4)

    assert bridge.marketResults["recent"] == []


def test_qml_bridge_market_history_is_deduplicated_and_capped(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())
    monkeypatch.setattr(
        "workers.market_search_worker.PaperMarketService.search",
        lambda self, topic, filters=None: {k: MarketPage() for k in ("recent", "popular", "cited")},
    )

    for topic in [f"konu{i}" for i in range(12)] + ["KONU5"]:
        bridge.searchArticles(topic)

    history = bridge.marketSearchHistory
    assert history[0] == "KONU5" and len(history) == 10
    assert [t.lower() for t in history].count("konu5") == 1

    bridge.clearMarketHistory()
    assert bridge.marketSearchHistory == []


def test_qml_bridge_search_articles_ignores_blank_topic(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())

    bridge.searchArticles("   ")

    assert bridge.marketSearchLoading is False
    assert bridge.marketResults == {"recent": [], "popular": [], "cited": []}


def test_qml_bridge_save_market_result_creates_resource(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)

    bridge.saveMarketResult({
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani"],
        "year": 2017,
        "citationCount": 100000,
        "url": "https://arxiv.org/pdf/1706.03762",
        "abstract": "Ozet metni.",
    })

    assert bridge.resourcesModel.rowCount() == 1
    # extra_metadata dogrudan modelde rol olarak yok; controller uzerinden dogrula.
    resource = bridge._controller.load_resources_with_filters({})[0]
    assert resource.title == "Attention Is All You Need"
    assert resource.extra_metadata["source"] == "openalex"
    assert resource.extra_metadata["citation_count"] == 100000


def test_qml_bridge_import_local_pdf_copies_and_creates_resource(qapp, session, monkeypatch, tmp_path):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)

    storage_dir = tmp_path / "pdf_storage"

    def _fake_pdf_storage_dir():
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    monkeypatch.setattr("ui_qml.bridge.pdf_storage_dir", _fake_pdf_storage_dir)

    original = tmp_path / "orijinal_makale.pdf"
    original.write_bytes(b"%PDF-1.4 fake bytes")

    assert bridge.importLocalPdf(original.as_uri()) is True

    assert bridge.resourcesModel.rowCount() == 1
    resource = bridge._controller.load_resources_with_filters({})[0]
    assert resource.title == "orijinal_makale"
    assert resource.extra_metadata["source"] == "local_pdf"
    assert resource.extra_metadata["original_filename"] == "orijinal_makale.pdf"
    assert resource.url.startswith("file://")

    # Orijinal dosya yerinde durmali (kopya, tasima degil).
    assert original.exists()
    # Kopya storage dizininde olusmus olmali.
    copied_files = list(storage_dir.glob("*.pdf"))
    assert len(copied_files) == 1
    assert copied_files[0].name.endswith("orijinal_makale.pdf")


def test_qml_bridge_delete_resource_removes_copied_local_pdf(qapp, session, monkeypatch, tmp_path):
    """Yerel PDF kaynagi silinince kopyalanan dosya da diskten kalkmali,
    QPdfDocument onbellegi de temizlenmeli -- aksi halde her import/delete
    dongusunde disk/RAM sizintisi birikiyordu (bkz. code review bulgusu)."""
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)

    storage_dir = tmp_path / "pdf_storage"

    def _fake_pdf_storage_dir():
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    monkeypatch.setattr("ui_qml.bridge.pdf_storage_dir", _fake_pdf_storage_dir)

    original = tmp_path / "orijinal_makale.pdf"
    original.write_bytes(b"%PDF-1.4 fake bytes")
    bridge.importLocalPdf(original.as_uri())

    resource = bridge._controller.load_resources_with_filters({})[0]
    copied_path = list(storage_dir.glob("*.pdf"))[0]
    assert copied_path.exists()

    # Onbellege gercek bir QPdfDocument koymaya gerek yok -- sadece anahtarin
    # (url) silme sonrasi temizlendigini dogrulamak icin sahte bir deger yeterli.
    bridge._pdf_document_cache[resource.url] = object()

    bridge.deleteResource(resource.id)

    assert not copied_path.exists()
    assert resource.url not in bridge._pdf_document_cache


def _add_web_pdf_resource(bridge, url="https://arxiv.org/pdf/1706.03762"):
    return bridge._controller.add_resource(
        {"title": "Attention", "url": url, "category_id": None, "priority": 2}
    )


def test_qml_bridge_open_reader_downloads_web_pdf_then_serves_native(qapp, session, monkeypatch, tmp_path):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)
    started = []
    monkeypatch.setattr(bridge, "_start_pdf_download", lambda res: started.append(res.id))
    res = _add_web_pdf_resource(bridge)

    bridge.openReader(res.id)

    assert bridge.currentView == "pdfReader"
    assert started == [res.id]
    assert bridge.currentReaderResource["pdfFileUrl"] == ""

    pdf = tmp_path / "attention.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    bridge._on_pdf_download_finished(res.id, str(pdf))

    assert bridge.currentReaderResource["pdfFileUrl"] == pdf.as_uri()
    assert bridge.currentReaderResource["pdfState"] == "ready"
    # Ikinci acilista tekrar indirme baslamamali.
    started.clear()
    bridge.openReader(res.id)
    assert started == []
    assert bridge.currentView == "pdfReader"


def test_qml_bridge_web_pdf_download_failure_falls_back_to_text_reader(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)
    monkeypatch.setattr(bridge, "_start_pdf_download", lambda res: None)
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))
    res = _add_web_pdf_resource(bridge)

    bridge.openReader(res.id)
    assert bridge.currentView == "pdfReader"
    bridge._on_pdf_download_finished(res.id, None)

    assert bridge.currentView == "reader"
    assert notifications and notifications[-1][0] == "error"
    # Basarisiz kaynak icin tekrar acinca indirme denenmez, dogrudan metin okuyucu.
    bridge.openReader(res.id)
    assert bridge.currentView == "reader"


def test_qml_bridge_delete_removes_downloaded_web_pdf(qapp, session, monkeypatch, tmp_path):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)
    storage = tmp_path / "store"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.bridge.pdf_storage_dir", lambda: storage)
    res = _add_web_pdf_resource(bridge)
    pdf = storage / "abc_attention.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    bridge._on_pdf_download_finished(res.id, str(pdf))

    bridge.deleteResource(res.id)

    assert not pdf.exists()


def test_qml_bridge_scrape_metadata_merges_instead_of_overwriting(qapp, session):
    bridge = QmlBridge(session)
    res = bridge._controller.add_resource(
        {"title": "T", "url": "https://example.com/a", "category_id": None, "priority": 2,
         "extra_metadata": {"authors": ["A. Yazar"], "local_pdf": "x"}}
    )

    bridge._on_scrape_finished(res.id, {"thumbnail": "https://img/x.jpg"})

    meta = bridge._controller.get_resource(res.id).extra_metadata
    assert meta["authors"] == ["A. Yazar"]
    assert meta["local_pdf"] == "x"
    assert meta["thumbnail"] == "https://img/x.jpg"


def _paper_resource(bridge):
    return bridge._controller.add_resource(
        {
            "title": "Attention Is All You Need",
            "url": "https://doi.org/10.5555/3295222.3295349",
            "category_id": None,
            "priority": 2,
            "extra_metadata": {
                "authors": ["Ashish Vaswani", "Noam Shazeer"],
                "year": 2017,
                "venue": "NeurIPS",
                "doi": "10.5555/3295222.3295349",
                "openalex_id": "W2626778328",
            },
        }
    )


def test_qml_bridge_citation_text_and_copy(qapp, session):
    from PySide6.QtGui import QGuiApplication

    bridge = QmlBridge(session)
    res = _paper_resource(bridge)
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    apa = bridge.citationText(res.id, "apa")
    assert apa.startswith("Vaswani, A., & Shazeer, N. (2017). Attention Is All You Need.")
    assert bridge.citationText(res.id, "bogus") == ""
    assert bridge.citationText(9999, "apa") == ""

    bridge.copyCitation(res.id, "bibtex")
    assert QGuiApplication.clipboard().text().startswith("@article{vaswani2017attention,")
    assert notifications[-1] == ("info", "Atıf panoya kopyalandı (BIBTEX).")


def test_qml_bridge_paper_metadata_merges_into_extra_metadata(qapp, session):
    from services.paper_market_service import PaperResult

    bridge = QmlBridge(session)
    res = bridge._controller.add_resource(
        {"title": "Makale", "url": "https://arxiv.org/pdf/1", "category_id": None, "priority": 2,
         "extra_metadata": {"local_pdf": "x"}}
    )
    paper = PaperResult(title="Makale", authors=["A. Yazar"], year=2020, citation_count=5, url=None,
                        abstract=None, doi="10.1/abc", openalex_id="W1", venue="Dergi")

    bridge._on_paper_metadata_finished(res.id, paper, "")

    meta = bridge._controller.get_resource(res.id).extra_metadata
    assert meta["local_pdf"] == "x"
    assert meta["doi"] == "10.1/abc" and meta["openalex_id"] == "W1" and meta["venue"] == "Dergi"


def test_qml_bridge_paper_metadata_errors_surface_as_toasts(qapp, session):
    bridge = QmlBridge(session)
    res = _paper_resource(bridge)
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    bridge._on_paper_metadata_finished(res.id, None, "timeout")
    bridge._on_paper_metadata_finished(res.id, None, "")

    assert notifications[0][0] == "error"
    assert notifications[1][0] == "info" and "bulunamadı" in notifications[1][1]


def test_qml_bridge_related_papers_loading_and_stale_result_ignored(qapp, session, monkeypatch):
    from services.paper_market_service import PaperResult

    bridge = QmlBridge(session)
    started = []
    monkeypatch.setattr(bridge._thread_pool, "start", lambda worker: started.append(worker))
    res = _paper_resource(bridge)

    bridge.loadRelatedPapers(res.id)
    assert len(started) == 2
    assert bridge.relatedPapers["references"]["loading"] is True

    paper = PaperResult(title="Ref", authors=[], year=2016, citation_count=9, url="https://x", abstract=None,
                        openalex_id="W9")
    bridge._on_related_papers_finished("W2626778328", "references", [paper], "")
    assert bridge.relatedPapers["references"]["loaded"] is True
    assert bridge.relatedPapers["references"]["items"][0]["openalexId"] == "W9"

    bridge._on_related_papers_finished("W2626778328", "citations", [], "boom")
    assert bridge.relatedPapers["citations"]["error"] != ""

    # Baska makale acilmisken gelen eski sonuc yok sayilir.
    bridge._on_related_papers_finished("W-OTHER", "references", [paper], "")
    assert bridge.relatedPapers["references"]["items"][0]["title"] == "Ref"


def test_qml_bridge_related_papers_without_openalex_id_starts_nothing(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    started = []
    monkeypatch.setattr(bridge._thread_pool, "start", lambda worker: started.append(worker))
    res = bridge._controller.add_resource({"title": "T", "url": "https://x.org/a", "category_id": None, "priority": 2})

    bridge.loadRelatedPapers(res.id)

    assert started == []
    assert bridge.relatedPapers["openalexId"] == ""


def test_qml_bridge_export_markdown_writes_file_and_adds_extension(qapp, session, tmp_path):
    bridge = QmlBridge(session)
    res = _paper_resource(bridge)
    bridge._controller.create_highlight(res.id, "onemli cumle", "#22C55E", 0, 1, 5)
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    target = tmp_path / "literatur"
    bridge.exportResourceMarkdown(res.id, (tmp_path / "literatur").as_uri())

    written = tmp_path / "literatur.md"
    assert written.exists()
    text = written.read_text(encoding="utf-8")
    assert "# Attention Is All You Need" in text and "“onemli cumle” (s. 1)" in text
    assert notifications[-1] == ("info", "Dışa aktarıldı: literatur.md")
    assert not target.exists()


def test_qml_bridge_export_library_empty_notifies(qapp, session, tmp_path):
    bridge = QmlBridge(session)
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    bridge.exportLibraryMarkdown((tmp_path / "hepsi.md").as_uri())

    assert not (tmp_path / "hepsi.md").exists()
    assert notifications[-1][0] == "info"


def test_qml_bridge_export_write_failure_is_reported(qapp, session, tmp_path):
    bridge = QmlBridge(session)
    res = _paper_resource(bridge)
    bridge._controller.create_highlight(res.id, "x", "#22C55E", 0, 1, 1)
    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    bridge.exportResourceMarkdown(res.id, (tmp_path / "yok_klasor" / "a.md").as_uri())

    assert notifications[-1][0] == "error"


def test_qml_bridge_add_pdf_vocabulary_stores_sentence_context(qapp, session):
    """Gercek bir PDF uzerinde: secilen kelime + gectigi cumle kelime havuzuna yazilir."""
    import pytest
    from PySide6.QtCore import QPointF
    from PySide6.QtPdf import QPdfDocument
    from core.paths import pdf_storage_dir

    candidates = list(pdf_storage_dir().glob("*Hybrid*.pdf")) if pdf_storage_dir().exists() else []
    if not candidates:
        pytest.skip("Gercek test PDF'i yok")
    pdf = candidates[0]
    bridge = QmlBridge(session)
    res = bridge._controller.add_resource(
        {"title": "PDF", "url": pdf.as_uri(), "category_id": None, "priority": 2}
    )
    doc = bridge._load_pdf_document(pdf.as_uri())
    size = doc.pagePointSize(0)
    x0, y0, x1, y1 = size.width() * 0.2, size.height() * 0.40, size.width() * 0.5, size.height() * 0.41

    bridge.addPdfVocabulary(res.id, pdf.as_uri(), 0, x0, y0, x1, y1, "ceviri")

    vocab = bridge._controller.get_resource(res.id).vocabulary
    assert len(vocab) == 1
    assert vocab[0].translation == "ceviri"
    assert vocab[0].context_sentence and len(vocab[0].context_sentence) > len(vocab[0].word)
    assert "\n" not in vocab[0].context_sentence


def test_qml_bridge_import_local_pdf_rejects_non_pdf(qapp, session, monkeypatch, tmp_path):
    bridge = QmlBridge(session)

    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    not_pdf = tmp_path / "not_a_pdf.txt"
    not_pdf.write_text("merhaba")

    assert bridge.importLocalPdf(not_pdf.as_uri()) is False

    assert bridge.resourcesModel.rowCount() == 0
    assert notifications and notifications[0][0] == "error"


def test_qml_bridge_apply_filter_status_and_favorites(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_scrape", lambda *args: None)

    # 1. Farklı durumlarda ve favoride kaynaklar ekle
    bridge.saveResource({
        "title": "Gelen Kutusu Kaynağı",
        "url": "https://example.com/inbox",
        "status": "INBOX",
    })
    inbox_id = bridge.selectedResource["id"]

    bridge.saveResource({
        "title": "Tamamlanan Kaynak",
        "url": "https://example.com/done",
        "status": "COMPLETED",
    })
    done_id = bridge.selectedResource["id"]

    # done_id'yi favoriye ekle
    bridge.toggleFavorite(done_id)

    # Toplam 2 kaynak
    assert bridge.resourcesModel.rowCount() == 2

    # Durum filtresi: Sadece INBOX
    bridge.applyFilter("", "0", "0", "INBOX", False)
    assert bridge.resourcesModel.rowCount() == 1
    assert bridge.resourcesModel.data(bridge.resourcesModel.index(0, 0), bridge.resourcesModel.IdRole) == inbox_id

    # Durum filtresi: Sadece COMPLETED
    bridge.applyFilter("", "0", "0", "COMPLETED", False)
    assert bridge.resourcesModel.rowCount() == 1
    assert bridge.resourcesModel.data(bridge.resourcesModel.index(0, 0), bridge.resourcesModel.IdRole) == done_id

    # Favori filtresi: Sadece favoriler (status ALL)
    bridge.applyFilter("", "0", "0", "ALL", True)
    assert bridge.resourcesModel.rowCount() == 1
    assert bridge.resourcesModel.data(bridge.resourcesModel.index(0, 0), bridge.resourcesModel.IdRole) == done_id

    # Favori filtresi + INBOX (hiçbiri eşleşmemeli)
    bridge.applyFilter("", "0", "0", "INBOX", True)
    assert bridge.resourcesModel.rowCount() == 0

    # Sıfırlama: ALL ve favori değil
    bridge.applyFilter("", "0", "0", "ALL", False)
    assert bridge.resourcesModel.rowCount() == 2


def test_qml_bridge_pdf_note_crud(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)

    bridge.saveMarketResult({
        "title": "PDF Not Testi", "authors": [], "year": None, "citationCount": 0,
        "url": "https://example.com/x.pdf", "abstract": "",
    })
    res_id = bridge._controller.load_resources_with_filters({})[0].id

    bridge.addPdfNote(res_id, 3, 120.5, 60.0, "onemli bir not")
    notes = bridge._controller.load_resource_pdf_notes(res_id)
    assert len(notes) == 1
    assert notes[0].page == 3
    assert notes[0].note_text == "onemli bir not"

    bridge.openReader(res_id)
    assert bridge.currentReaderResource["pdfNotes"][0]["text"] == "onemli bir not"

    bridge.updatePdfNote(notes[0].id, "guncellenmis not")
    assert bridge.currentReaderResource["pdfNotes"][0]["text"] == "guncellenmis not"

    bridge.deletePdfNote(notes[0].id)
    assert bridge.currentReaderResource["pdfNotes"] == []


def test_qml_bridge_add_pdf_note_ignores_blank_text(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_scrape", lambda *args: None)

    bridge.saveResource({"title": "Bos Not Testi", "url": "https://example.com/y.pdf"})
    res_id = bridge.selectedResource["id"]

    bridge.addPdfNote(res_id, 0, 0.0, 0.0, "   ")

    assert bridge._controller.load_resource_pdf_notes(res_id) == []



def test_qml_bridge_market_results_flag_papers_already_in_library(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)
    saved = PaperResult(
        title="Kayitli", authors=[], year=2020, citation_count=1, url="https://x.org/k",
        abstract=None, doi="10.1/kayitli",
    )
    fresh = _paper("yeni")
    bridge.saveMarketResult(
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

    bridge.searchArticles("gan")

    flagged, unflagged = bridge.marketResults["recent"]
    assert flagged["libraryResourceId"] > 0
    assert unflagged["libraryResourceId"] == 0


def test_qml_bridge_save_market_result_skips_duplicate_doi(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)
    notes = []
    bridge.notificationEmitted.connect(lambda kind, msg: notes.append((kind, msg)))
    paper = {"title": "Ayni", "url": "https://x.org/a", "doi": "10.9/ayni"}

    bridge.saveMarketResult(paper)
    bridge.saveMarketResult(paper)

    assert bridge.resourcesModel.count == 1
    assert "zaten" in notes[-1][1]


def test_qml_bridge_saving_a_result_refreshes_library_flag(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)
    bridge._market_results_cache = {
        "recent": [{"title": "T", "doi": "10.9/t", "openalexId": "", "libraryResourceId": 0}],
        "popular": [],
        "cited": [],
    }
    changes = []
    bridge.marketResultsChanged.connect(lambda: changes.append(1))

    bridge.saveMarketResult({"title": "T", "url": "https://x.org/t", "doi": "10.9/t"})

    assert bridge.marketResults["recent"][0]["libraryResourceId"] > 0
    assert changes


def test_qml_bridge_load_discovery_populates_and_caches(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())
    calls = []

    def fake_related(self, openalex_id, kind, limit=25):
        calls.append((kind, openalex_id))
        return [_paper("r1")]

    monkeypatch.setattr("workers.related_papers_worker.PaperMarketService.related_papers", fake_related)

    bridge.loadDiscovery("similar", "W1")
    bridge.loadDiscovery("similar", "W1")  # onbellekten: ikinci istek yok

    state = bridge.marketDiscovery["similar:W1"]
    assert state["loaded"] is True and state["loading"] is False
    assert [i["title"] for i in state["items"]] == ["r1"]
    assert calls == [("similar", "W1")]


def test_qml_bridge_load_discovery_reports_error(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())

    def boom(self, openalex_id, kind, limit=25):
        raise RuntimeError("offline")

    monkeypatch.setattr("workers.related_papers_worker.PaperMarketService.related_papers", boom)

    bridge.loadDiscovery("references", "W1")

    state = bridge.marketDiscovery["references:W1"]
    assert state["loaded"] is False and state["error"] and state["items"] == []


def test_qml_bridge_search_without_topic_or_author_is_ignored(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())

    bridge.searchArticles("", {"yearFrom": "2020"})

    assert bridge.marketSearchLoading is False


def test_qml_bridge_reset_market_results_clears_and_invalidates_pending(qapp, session):
    bridge = QmlBridge(session)
    bridge._market_results_cache["recent"] = [{"title": "x"}]
    pending_id = bridge._market_request_id

    bridge.resetMarketResults()
    bridge._on_market_search_finished({"recent": MarketPage(items=[_paper("late")], total=1)}, pending_id)

    assert bridge.marketResults["recent"] == []


def test_qml_bridge_library_suggestions_use_openalex_ids_of_library(qapp, session, monkeypatch):
    from services.reading_suggestion_service import Suggestion

    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)
    bridge.saveMarketResult({"title": "Kutuphane", "url": "https://x.org/1", "openalexId": "W1"})
    received = []

    def fake_suggest(self, ids, min_frequency=None, limit=20):
        received.append(ids)
        return [Suggestion(_paper("W9"), 2)]

    monkeypatch.setattr("workers.reading_suggestion_worker.ReadingSuggestionService.suggest", fake_suggest)

    bridge.loadLibrarySuggestions()

    state = bridge.marketSuggestions
    assert received == [["W1"]]
    assert state["loaded"] is True and state["sourceCount"] == 1
    assert state["items"][0]["citedByLibrary"] == 2


def test_qml_bridge_library_suggestions_without_openalex_sources_skips_network(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_thread_pool", _SyncThreadPool())

    bridge.loadLibrarySuggestions()

    state = bridge.marketSuggestions
    assert state["sourceCount"] == 0 and state["loading"] is False and state["items"] == []


def _notes(bridge):
    notes = []
    bridge.notificationEmitted.connect(lambda kind, msg: notes.append(msg))
    return notes


def test_qml_bridge_batch_save_adds_new_skips_existing_and_dedups_within_batch(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)
    notes = _notes(bridge)
    bridge.saveMarketResult({"title": "Var", "url": "https://x.org/var", "doi": "10.1/var"})
    notes.clear()

    bridge.saveMarketResults([
        {"title": "Var", "url": "https://x.org/var", "doi": "10.1/VAR"},
        {"title": "Yeni", "url": "https://x.org/yeni", "doi": "10.1/yeni"},
        {"title": "Yeni kopya", "url": "https://x.org/yeni2", "doi": "10.1/yeni"},
        {"title": "Baska", "url": "https://x.org/baska", "openalexId": "W5"},
    ])

    assert bridge.resourcesModel.count == 3
    assert notes == ["2 makale kaydedildi, 2 tanesi zaten kütüphanendeydi."]


def test_qml_bridge_batch_save_all_duplicates_message(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)
    paper = {"title": "Var", "url": "https://x.org/var", "doi": "10.1/var"}
    bridge.saveMarketResult(paper)
    notes = _notes(bridge)

    bridge.saveMarketResults([paper])

    assert notes == ["Seçilen makalelerin hepsi zaten kütüphanende."]


def test_qml_bridge_save_for_later_tags_resource(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge, "_schedule_full_text_extract", lambda *args: None)

    bridge.saveMarketResultForLater({"title": "Sonra", "url": "https://x.org/s"})

    resource = bridge._controller.load_resources_with_filters({})[0]
    assert "okuma-listesi" in [t.name for t in resource.tags]


def test_qml_bridge_export_market_results_writes_bibtex_and_csv(qapp, session, tmp_path):
    bridge = QmlBridge(session)
    papers = [{"title": "Baslik", "authors": ["Ada Lovelace"], "year": 1843, "doi": "10.1/x", "citationCount": 1}]

    bridge.exportMarketResults("bibtex", str(tmp_path / "sonuc"), papers)  # uzanti eklenir
    bridge.exportMarketResults("csv", str(tmp_path / "sonuc.csv"), papers)

    assert "@article{lovelace1843baslik" in (tmp_path / "sonuc.bib").read_text(encoding="utf-8")
    raw = (tmp_path / "sonuc.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and b"Baslik" in raw  # Excel icin BOM


def test_qml_bridge_export_market_results_empty_and_invalid(qapp, session, tmp_path):
    import pytest

    bridge = QmlBridge(session)
    notes = _notes(bridge)

    bridge.exportMarketResults("csv", str(tmp_path / "x.csv"), [])

    assert notes == ["Dışa aktarılacak sonuç yok."] and not (tmp_path / "x.csv").exists()
    with pytest.raises(ValueError):
        bridge.exportMarketResults("pdf", str(tmp_path / "x.pdf"), [{"title": "t"}])
