"""Alt-bridge'lerin olay (event_bus) ile koordinasyonu ve SettingsBridge/FullTextExtractor davranışları.

Bridge bölündükten sonra kategori/etiket/kaynak değişiklikleri doğrudan çağrı yerine olaylarla yayılıyor;
bu testler o sözleşmeyi (filtre sıfırlama, okuyucunun kapanması, açık paneller tazelenmesi) sabitler.
"""
from unittest.mock import patch

import pytest

from tests.test_qml.qml_harness import SyncThreadPool
from ui_qml.bridge import QmlBridge


@pytest.fixture()
def bridge(qapp, session, monkeypatch):
    b = QmlBridge(session)
    b.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(b.ctx.extractor, "schedule", lambda *args: None)
    return b


def _notes(bridge):
    notes = []
    bridge.notificationEmitted.connect(lambda kind, msg: notes.append((kind, msg)))
    return notes


def _add(bridge, title="Kaynak", **extra):
    return bridge.controllers.resources.add_resource(
        {"title": title, "url": f"https://x.org/{title}", "category_id": None, "priority": 2, **extra}
    )


# ---------------------------------------------------------------- SettingsBridge
def test_create_category_and_tag_refresh_lists_and_notify(bridge):
    notes = _notes(bridge)

    bridge.settings.createCategory("  Makale ", "#123456", "")
    bridge.settings.createTag(" ai ")

    assert [c["name"] for c in bridge.settings.categories] == ["Makale"]
    assert bridge.settings.categories[0]["color_hex"] == "#123456"
    assert [t["name"] for t in bridge.settings.tags] == ["ai"]
    assert [kind for kind, _ in notes] == ["info", "info"]


def test_blank_names_are_ignored(bridge):
    bridge.settings.createCategory("   ", "#123456", "")
    bridge.settings.createTag("")
    bridge.settings.updateCategory(1, "  ", "#000000", "")
    bridge.settings.updateTag(1, "")

    assert bridge.settings.categories == [] and bridge.settings.tags == []


def test_duplicate_category_shows_error_toast(bridge):
    bridge.settings.createCategory("Makale", "#123456", "")
    notes = _notes(bridge)

    bridge.settings.createCategory("Makale", "#654321", "")

    assert [kind for kind, _ in notes] == ["error"]
    assert len(bridge.settings.categories) == 1


def test_category_rename_refreshes_resource_list_and_open_drawer(bridge):
    bridge.settings.createCategory("Eski", "#111111", "")
    category = bridge.settings.categories[0]
    resource = _add(bridge, category_id=category["id"])
    bridge.library.selectResource(resource.id)
    assert bridge.library.selectedResource["categoryName"] == "Eski"

    bridge.settings.updateCategory(category["id"], "Yeni", "#222222", "")

    assert bridge.library.selectedResource["categoryName"] == "Yeni"
    assert bridge.library.selectedResource["categoryColor"] == "#222222"
    assert bridge.library.resourcesModel.data(bridge.library.resourcesModel.index(0, 0),
                                              bridge.library.resourcesModel.CategoryNameRole) == "Yeni"


def test_deleting_the_filtered_category_resets_the_library_filter(bridge):
    bridge.settings.createCategory("Filtreli", "#111111", "")
    category = bridge.settings.categories[0]
    _add(bridge, "Icinde", category_id=category["id"])
    _add(bridge, "Disinda")
    bridge.library.applyFilter("", str(category["id"]), "0", "ALL", False)
    assert bridge.library.resourcesModel.count == 1

    bridge.settings.deleteCategory(category["id"])

    assert bridge.library.resourcesModel.count == 2  # filtre sifirlandi, tum kaynaklar geri geldi


def test_deleting_the_filtered_tag_resets_the_library_filter(bridge):
    bridge.settings.createTag("etiketli")
    tag = bridge.settings.tags[0]
    _add(bridge, "Etiketli", tag_names=["etiketli"])
    _add(bridge, "Etiketsiz")
    bridge.library.applyFilter("", "0", str(tag["id"]), "ALL", False)
    assert bridge.library.resourcesModel.count == 1

    bridge.settings.deleteTag(tag["id"])

    assert bridge.library.resourcesModel.count == 2


def test_deleting_an_unfiltered_category_keeps_other_filters(bridge):
    bridge.settings.createCategory("A", "#111111", "")
    bridge.settings.createCategory("B", "#222222", "")
    a, b = bridge.settings.categories
    _add(bridge, "Akaynagi", category_id=a["id"])
    bridge.library.applyFilter("", str(a["id"]), "0", "ALL", False)

    bridge.settings.deleteCategory(b["id"])

    assert bridge.library.resourcesModel.count == 1  # A filtresi korunuyor


def test_tag_rename_refreshes_open_reader(bridge):
    bridge.settings.createTag("eski")
    resource = _add(bridge, tag_names=["eski"])
    bridge.reader.openReader(resource.id)
    names = lambda: {t["name"] for t in bridge.reader.currentReaderResource["tags"]}  # noqa: E731
    assert "eski" in names()  # (URL'den gelen alan adi etiketi de olabilir)
    tag = next(t for t in bridge.settings.tags if t["name"] == "eski")

    bridge.settings.updateTag(tag["id"], "yeni")

    assert "yeni" in names() and "eski" not in names()


# ---------------------------------------------------------------- Reader <-> Library olaylari
def test_deleting_the_open_resource_closes_reader_and_returns_to_showcase(bridge):
    resource = _add(bridge)
    bridge.reader.openReader(resource.id)
    assert bridge.currentView == "reader"

    bridge.library.deleteResource(resource.id)

    assert bridge.reader.currentReaderResource == {}
    assert bridge.currentView == "showcase"


def test_deleting_another_resource_leaves_the_open_reader_alone(bridge):
    open_one, other = _add(bridge, "acik"), _add(bridge, "diger")
    bridge.reader.openReader(open_one.id)

    bridge.library.deleteResource(other.id)

    assert bridge.reader.currentReaderResource["id"] == open_one.id
    assert bridge.currentView == "reader"


def test_opening_the_reader_closes_the_drawer(bridge):
    resource = _add(bridge)
    bridge.library.selectResource(resource.id)
    assert bridge.library.isDrawerOpen is True

    bridge.reader.openReader(resource.id)

    assert bridge.library.isDrawerOpen is False


def test_deleting_the_selected_resource_closes_the_drawer(bridge):
    resource = _add(bridge)
    bridge.library.selectResource(resource.id)

    bridge.library.deleteResource(resource.id)

    assert bridge.library.isDrawerOpen is False and bridge.library.resourcesModel.count == 0


# ---------------------------------------------------------------- FullTextExtractor
def test_full_text_extraction_saves_text_updates_reading_time_and_refreshes_open_reader(qapp, session):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    resource = _add(bridge)
    bridge.reader.openReader(resource.id)  # bos tam metin: cikarim planlanir (gercek extractor calisir)
    updates = []
    bridge.reader.readerArticleUpdated.connect(lambda rid, text: updates.append((rid, text)))

    with patch("workers.extract_worker.ArticleExtractionService") as service:
        service.return_value.extract_full_text.return_value = "kelime " * 400
        bridge.ctx.extractor.schedule(resource.id, "https://x.org/Kaynak")

    saved = bridge.controllers.resources.get_resource(resource.id)
    assert saved.full_text.startswith("kelime") and saved.reading_minutes == 2
    assert updates == [(resource.id, "kelime " * 400)]
    assert bridge.reader.currentReaderResource["readingMinutes"] == 2


def test_full_text_extraction_failure_changes_nothing(qapp, session):
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    resource = _add(bridge)
    updates = []
    bridge.reader.readerArticleUpdated.connect(lambda rid, text: updates.append(rid))

    with patch("workers.extract_worker.ArticleExtractionService") as service:
        service.return_value.extract_full_text.return_value = None
        bridge.ctx.extractor.schedule(resource.id, "https://x.org/Kaynak")

    assert bridge.controllers.resources.get_resource(resource.id).full_text is None
    assert updates == []
