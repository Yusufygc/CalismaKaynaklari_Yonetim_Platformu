from ui_qml.bridge import QmlBridge


def test_qml_bridge_initial_state(qapp, session):
    bridge = QmlBridge(session)

    assert bridge.isDarkTheme is True
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

    bridge.deleteVocabulary(bridge.vocabulary[0]["id"])
    assert len(bridge.vocabulary) == 0
