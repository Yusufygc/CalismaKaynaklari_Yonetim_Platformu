"""Ayarlar > Obsidian sekmesi (gercek QML): durum gosterimi ve elle esitleme dugmesi."""
from PySide6.QtTest import QTest

from tests.test_qml.qml_harness import click, find_named, open_window, pump
from tests.test_qml.test_vault_bridge import _note_files, env  # noqa: F401  (fixture)


def _open_vault_tab(qapp, bridge):
    engine, window = open_window(qapp, bridge, "settings", width=1300, height=800)
    click(qapp, window, find_named(window, "vaultTab"))
    pump(qapp, 40)
    return engine, window


def test_tab_shows_that_syncing_is_off_until_a_folder_is_chosen(env, qapp):
    bridge, _resource, _vault, _toasts, _tmp = env

    engine, window = _open_vault_tab(qapp, bridge)

    assert find_named(window, "vaultPathText").property("text") == "Klasör seçilmedi"
    assert find_named(window, "vaultStateText").property("text") == "Eşitleme kapalı"
    assert not find_named(window, "syncVaultButton").property("enabledState")
    assert not find_named(window, "clearVaultButton").property("visible")
    assert engine.captured_warnings == []


def test_tab_reflects_a_chosen_folder_and_the_sync_button_rewrites_a_deleted_note(env, qapp):
    bridge, _resource, vault, _toasts, _tmp = env
    engine, window = _open_vault_tab(qapp, bridge)

    bridge.vault.chooseVault(str(vault))
    pump(qapp, 40)

    assert find_named(window, "vaultPathText").property("text") == str(vault)
    assert "not yazıldı" in find_named(window, "vaultStateText").property("text")
    assert find_named(window, "syncVaultButton").property("enabledState")
    (note,) = _note_files(vault)
    note.unlink()  # kullanici notu yanlislikla sildi: elle esitleme yeniden uretir

    click(qapp, window, find_named(window, "syncVaultButton"))
    pump(qapp, 40)

    assert len(_note_files(vault)) == 1
    click(qapp, window, find_named(window, "clearVaultButton"))
    pump(qapp, 40)
    assert find_named(window, "vaultStateText").property("text") == "Eşitleme kapalı" and len(_note_files(vault)) == 1
    assert engine.captured_warnings == []
