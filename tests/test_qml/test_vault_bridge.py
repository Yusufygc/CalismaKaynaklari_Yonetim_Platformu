"""bridge.vault: vault klasoru secimi, kalicilik, geri yukleme ve degisikliklerin vault'a akmasi (gercek servislerle)."""
import pytest
from PySide6.QtTest import QTest

from core.user_settings import UserSettings
from tests.pdf_factory import write_text_pdf
from tests.test_qml.qml_harness import SyncThreadPool
from ui_qml.bridge import QmlBridge


@pytest.fixture()
def env(qapp, session, tmp_path, monkeypatch):
    storage = tmp_path / "depo"
    storage.mkdir()
    monkeypatch.setattr("ui_qml.pdf_files.pdf_storage_dir", lambda: storage)
    bridge = QmlBridge(session)
    bridge.ctx.thread_pool = SyncThreadPool()
    monkeypatch.setattr(bridge.ctx.extractor, "schedule", lambda *args: None)
    bridge.ctx.vault_sync._timer.setInterval(20)
    bridge.library.importLocalPdf(write_text_pdf(tmp_path / "makale.pdf").as_uri())
    resource = bridge.controllers.resources.load_resources_with_filters({})[0]
    vault = tmp_path / "vault"
    vault.mkdir()
    toasts = []
    bridge.notificationEmitted.connect(lambda kind, text: toasts.append((kind, text)))
    return bridge, resource, vault, toasts, tmp_path


def _note_files(vault):
    return sorted((vault / "Papers").glob("*.md")) if (vault / "Papers").exists() else []


def test_choosing_a_vault_saves_the_setting_syncs_existing_documents_and_reports_status(env):
    bridge, resource, vault, toasts, tmp_path = env
    (vault / ".obsidian").mkdir()

    bridge.vault.chooseVault(vault.as_uri())

    assert bridge.vault.status["enabled"] and bridge.vault.status["path"] == str(vault)
    assert UserSettings(tmp_path / "user_settings.json").get("vault_path") == str(vault)
    (note,) = _note_files(vault)
    assert "makale" in note.read_text(encoding="utf-8")
    assert toasts[-1][0] == "info" and "ayarlandı" in toasts[-1][1]


def test_a_folder_without_obsidian_marker_is_accepted_with_a_warning(env):
    bridge, _resource, vault, toasts, _tmp = env

    bridge.vault.chooseVault(str(vault))

    assert bridge.vault.status["enabled"] and ".obsidian" in toasts[0][1]


def test_an_unusable_folder_is_rejected_and_the_previous_setting_survives(env):
    bridge, _resource, vault, toasts, tmp_path = env
    bridge.vault.chooseVault(str(vault))
    toasts.clear()

    bridge.vault.chooseVault(str(tmp_path / "yok"))

    assert toasts[-1][0] == "error" and bridge.vault.status["path"] == str(vault)
    assert UserSettings(tmp_path / "user_settings.json").get("vault_path") == str(vault)


def test_clearing_the_vault_disables_syncing_and_keeps_the_notes(env):
    bridge, _resource, vault, _toasts, tmp_path = env
    bridge.vault.chooseVault(str(vault))

    bridge.vault.clearVault()

    assert not bridge.vault.status["enabled"] and bridge.vault.status["state"] == "disabled"
    assert UserSettings(tmp_path / "user_settings.json").get("vault_path") is None
    assert len(_note_files(vault)) == 1


def test_manual_sync_without_a_vault_asks_for_one_and_with_a_vault_reports_the_result(env):
    bridge, _resource, vault, toasts, _tmp = env

    bridge.vault.syncNow()
    assert toasts[-1] == ("info", "Önce bir Obsidian vault klasörü seç.")

    bridge.vault.chooseVault(str(vault))
    toasts.clear()
    bridge.vault.syncNow()

    assert toasts[-1][0] == "info" and "değişmedi" in toasts[-1][1]


def test_pdf_changes_flow_to_the_note_after_the_debounce(env):
    bridge, resource, vault, _toasts, _tmp = env
    bridge.vault.chooseVault(str(vault))
    bridge.pdf.openDocument(resource.id)

    bridge.pdf.addNote(0, 5.0, 5.0, "vault'a gidecek not")
    assert "vault'a gidecek not" not in _note_files(vault)[0].read_text(encoding="utf-8")  # henuz degil: birlestiriliyor
    QTest.qWait(150)

    assert "vault'a gidecek not" in _note_files(vault)[0].read_text(encoding="utf-8")


def test_changing_the_resource_title_updates_the_notes_frontmatter_but_not_its_filename(env):
    bridge, resource, vault, _toasts, _tmp = env
    bridge.vault.chooseVault(str(vault))
    (before,) = _note_files(vault)

    bridge.controllers.resources.update_resource(resource.id, {"title": "Yeni Baslik"})
    QTest.qWait(150)

    (after,) = _note_files(vault)
    assert after.name == before.name  # citekey degismez
    assert 'title: "Yeni Baslik"' in after.read_text(encoding="utf-8")


def test_saved_vault_is_restored_on_startup_and_a_missing_one_is_reported_but_kept(env, session, tmp_path, monkeypatch):
    bridge, _resource, vault, _toasts, _tmp = env
    bridge.vault.chooseVault(str(vault))
    settings_path = tmp_path / "user_settings.json"

    second = QmlBridge(session)
    second.ctx.thread_pool = SyncThreadPool()
    second.vault.restore()
    assert second.vault.status["enabled"] and second.vault.status["path"] == str(vault)

    vault.rename(tmp_path / "tasindi")
    third = QmlBridge(session)
    third.vault.restore()

    status = third.vault.status
    assert not status["enabled"] and status["state"] == "error" and status["path"] == str(vault) and "bulunamadı" in status["message"]
    assert UserSettings(settings_path).get("vault_path") == str(vault)  # ayar silinmedi (disk geri takilabilir)
