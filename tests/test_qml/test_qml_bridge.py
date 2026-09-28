from pathlib import Path

from ui_qml.bridge import QmlBridge
from services.paper_market_service import PaperResult


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

    bridge.toggleSimpleMode()
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
        lambda self, topic: {"recent": [fake_paper], "popular": [], "cited": [fake_paper]},
    )

    assert bridge.marketSearchLoading is False
    bridge.searchArticles("transformer")

    assert bridge.marketSearchLoading is False
    assert len(bridge.marketResults["recent"]) == 1
    assert bridge.marketResults["recent"][0]["title"] == "Attention Is All You Need"
    assert bridge.marketResults["recent"][0]["citationCount"] == 100000
    assert bridge.marketResults["popular"] == []
    assert len(bridge.marketResults["cited"]) == 1


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

    bridge.importLocalPdf(original.as_uri())

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


def test_qml_bridge_import_local_pdf_rejects_non_pdf(qapp, session, monkeypatch, tmp_path):
    bridge = QmlBridge(session)

    notifications = []
    bridge.notificationEmitted.connect(lambda t, m: notifications.append((t, m)))

    not_pdf = tmp_path / "not_a_pdf.txt"
    not_pdf.write_text("merhaba")

    bridge.importLocalPdf(not_pdf.as_uri())

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

