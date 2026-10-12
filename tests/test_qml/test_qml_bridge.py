"""Kaynak CRUD, etiket/kategori, alinti/kelime, filtre ve PDF notu akislari (QmlBridge kabugu)."""
import pytest

from ui_qml.bridge import QmlBridge


def test_qml_bridge_initial_shell_state(qapp, session):
    bridge = QmlBridge(session)

    assert bridge.isDarkTheme is True
    assert bridge.isSimpleMode is False
    assert bridge.currentView == "showcase"
    assert bridge.library.isDrawerOpen is False
    assert bridge.library.selectedResource == {}


def test_qml_bridge_initial_collections(qapp, session):
    bridge = QmlBridge(session)

    assert bridge.library.resourcesModel is not None
    assert isinstance(bridge.settings.categories, list)
    assert isinstance(bridge.settings.tags, list)
    assert isinstance(bridge.annotations.highlights, list)
    assert isinstance(bridge.annotations.vocabulary, list)
    assert "total" in bridge.library.stats


def test_qml_bridge_theme_toggle(qapp, session):
    bridge = QmlBridge(session)

    bridge.toggleTheme()
    assert bridge.isDarkTheme is False
    bridge.toggleTheme()
    assert bridge.isDarkTheme is True


def test_qml_bridge_view_switch(qapp, session):
    bridge = QmlBridge(session)

    bridge.setCurrentView("knowledge")
    assert bridge.currentView == "knowledge"
    bridge.setCurrentView("settings")
    assert bridge.currentView == "settings"


def test_qml_bridge_simple_mode_emits_only_on_change(qapp, session):
    bridge = QmlBridge(session)
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


@pytest.fixture()
def saved_resource(qapp, session, monkeypatch):
    """Kutuphaneye bir kaynak ekler (kazima zamanlanmaz); (bridge, kaynak_id) dondurur."""
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.library._scraper, "schedule", lambda *args: None)
    bridge.library.saveResource({
        "title": "QML Kaynağı",
        "url": "https://example.com/qml",
        "status": "PLANNED",
        "priority": 3,
        "content": "Notlar",
    })
    return bridge, bridge.library.selectedResource.get("id")


def test_qml_bridge_save_resource_opens_drawer(saved_resource):
    bridge, res_id = saved_resource

    assert bridge.library.resourcesModel.rowCount() >= 1
    assert res_id is not None
    assert bridge.library.isDrawerOpen is True
    assert bridge.library.selectedResource["title"] == "QML Kaynağı"


def test_qml_bridge_pin_and_favorite_update_selected_resource(saved_resource):
    bridge, res_id = saved_resource

    bridge.library.togglePin(res_id)
    assert bridge.library.selectedResource["isPinned"] is True

    bridge.library.toggleFavorite(res_id)
    assert bridge.library.selectedResource["isFavorite"] is True


def test_qml_bridge_status_and_notes_update_selected_resource(saved_resource):
    bridge, res_id = saved_resource

    bridge.library.updateResourceStatus(res_id, "COMPLETED")
    assert bridge.library.selectedResource["status"] == "COMPLETED"

    bridge.library.updateResourceNotes(res_id, "Yeni Notlar")
    assert bridge.library.selectedResource["content"] == "Yeni Notlar"


def test_qml_bridge_close_drawer_then_delete_resource(saved_resource):
    bridge, res_id = saved_resource

    bridge.library.closeDrawer()
    assert bridge.library.isDrawerOpen is False

    bridge.library.deleteResource(res_id)
    assert bridge.library.resourcesModel.rowCount() == 0


def test_qml_bridge_categories_and_tags(qapp, session):
    bridge = QmlBridge(session)

    # Kategori
    bridge.settings.createCategory("Teknoloji", "#6366F1", "fa5s.laptop")
    assert len(bridge.settings.categories) == 1
    cat_id = bridge.settings.categories[0]["id"]
    assert bridge.settings.categories[0]["name"] == "Teknoloji"

    # Etiket
    bridge.settings.createTag("python")
    assert len(bridge.settings.tags) == 1
    tag_id = bridge.settings.tags[0]["id"]
    assert bridge.settings.tags[0]["name"] == "python"

    # Silme
    bridge.settings.deleteCategory(cat_id)
    assert len(bridge.settings.categories) == 0

    bridge.settings.deleteTag(tag_id)
    assert len(bridge.settings.tags) == 0


def test_qml_bridge_highlights_and_vocabulary(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.library._scraper, "schedule", lambda *args: None)

    bridge.library.saveResource({"title": "Okuma Makalesi", "url": "https://example.com/article"})
    res_id = bridge.library.selectedResource["id"]

    # Alıntı ekleme
    bridge.annotations.addHighlight(res_id, "Onemli bir cumle", "#EAB308")
    assert len(bridge.annotations.highlights) == 1
    assert bridge.annotations.highlights[0]["content"] == "Onemli bir cumle"

    # Kelime ekleme
    bridge.annotations.addVocabulary(res_id, "ubiquitous", "her yerde bulunan", "It is ubiquitous.")
    assert len(bridge.annotations.vocabulary) == 1
    assert bridge.annotations.vocabulary[0]["word"] == "ubiquitous"

    # Silme
    bridge.annotations.deleteHighlight(bridge.annotations.highlights[0]["key"])
    assert len(bridge.annotations.highlights) == 0


def test_qml_bridge_add_highlight_with_pdf_position(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)

    bridge.market.saveMarketResult({
        "title": "PDF Kaynak", "authors": [], "year": None, "citationCount": 0,
        "url": "https://example.com/x.pdf", "abstract": "",
    })
    res_id = bridge.controllers.resources.load_resources_with_filters({})[0].id

    bridge.annotations.addHighlight(res_id, "sayfa alintisi", "#EAB308", {"page": 2, "startIndex": 100, "length": 30})

    hl = bridge.controllers.highlights.load_resource_highlights(res_id)[0]
    assert hl.page_number == 2
    assert hl.start_index == 100
    assert hl.length == 30

    # currentReaderResource serialize edilirken de dogru donmeli
    bridge.reader.openReader(res_id)
    serialized = bridge.reader.currentReaderResource["highlights"][0]
    assert serialized["page"] == 2
    assert serialized["startIndex"] == 100
    assert serialized["length"] == 30


def test_qml_bridge_scrape_metadata_merges_instead_of_overwriting(qapp, session):
    bridge = QmlBridge(session)
    res = bridge.controllers.resources.add_resource(
        {"title": "T", "url": "https://example.com/a", "category_id": None, "priority": 2,
         "extra_metadata": {"authors": ["A. Yazar"], "local_pdf": "x"}}
    )

    bridge.library._scraper._on_scrape_finished(res.id, {"thumbnail": "https://img/x.jpg"})

    meta = bridge.controllers.resources.get_resource(res.id).extra_metadata
    assert meta["authors"] == ["A. Yazar"]
    assert meta["local_pdf"] == "x"
    assert meta["thumbnail"] == "https://img/x.jpg"


def test_qml_bridge_apply_filter_status_and_favorites(qapp, session, monkeypatch):
    bridge = QmlBridge(session)
    monkeypatch.setattr(bridge.library._scraper, "schedule", lambda *args: None)

    # 1. Farklı durumlarda ve favoride kaynaklar ekle
    bridge.library.saveResource({
        "title": "Gelen Kutusu Kaynağı",
        "url": "https://example.com/inbox",
        "status": "INBOX",
    })
    inbox_id = bridge.library.selectedResource["id"]

    bridge.library.saveResource({
        "title": "Tamamlanan Kaynak",
        "url": "https://example.com/done",
        "status": "COMPLETED",
    })
    done_id = bridge.library.selectedResource["id"]

    # done_id'yi favoriye ekle
    bridge.library.toggleFavorite(done_id)

    # Toplam 2 kaynak
    assert bridge.library.resourcesModel.rowCount() == 2

    # Durum filtresi: Sadece INBOX
    bridge.library.applyFilter("", "0", "0", "INBOX", False)
    assert bridge.library.resourcesModel.rowCount() == 1
    assert bridge.library.resourcesModel.data(bridge.library.resourcesModel.index(0, 0), bridge.library.resourcesModel.IdRole) == inbox_id

    # Durum filtresi: Sadece COMPLETED
    bridge.library.applyFilter("", "0", "0", "COMPLETED", False)
    assert bridge.library.resourcesModel.rowCount() == 1
    assert bridge.library.resourcesModel.data(bridge.library.resourcesModel.index(0, 0), bridge.library.resourcesModel.IdRole) == done_id

    # Favori filtresi: Sadece favoriler (status ALL)
    bridge.library.applyFilter("", "0", "0", "ALL", True)
    assert bridge.library.resourcesModel.rowCount() == 1
    assert bridge.library.resourcesModel.data(bridge.library.resourcesModel.index(0, 0), bridge.library.resourcesModel.IdRole) == done_id

    # Favori filtresi + INBOX (hiçbiri eşleşmemeli)
    bridge.library.applyFilter("", "0", "0", "INBOX", True)
    assert bridge.library.resourcesModel.rowCount() == 0

    # Sıfırlama: ALL ve favori değil
    bridge.library.applyFilter("", "0", "0", "ALL", False)
    assert bridge.library.resourcesModel.rowCount() == 2
