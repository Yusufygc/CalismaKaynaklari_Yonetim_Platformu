from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from core.logger import log
from pdfkit.api import SyncReport, VaultUnavailableError
from ui_qml.context import BridgeContext

SETTING_VAULT_PATH = "vault_path"


class VaultBridge(QObject):
    """Ayarlar > Obsidian: vault klasoru secimi, durum ve elle esitleme. Esitlemenin kendisi `pdfkit`'tedir
    (`VaultSync`); burasi yalnizca ayari saklar ve kullaniciya bildirir."""

    statusChanged = Signal()

    def __init__(self, ctx: BridgeContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._sync = ctx.vault_sync
        self._unavailable = ""  # kayitli klasor acilista kullanilamadiysa nedeni
        self._manual_sync = False
        self._startup_hooked = False
        self._sync.statusChanged.connect(self.statusChanged)
        self._sync.syncFinished.connect(self._on_sync_finished)

    @Property(dict, notify=statusChanged)
    def status(self) -> dict:
        """{enabled, path, state (disabled|idle|pending|syncing|error), message, lastSync}."""
        status = self._sync.status()
        saved = self._ctx.user_settings.get(SETTING_VAULT_PATH, "")
        if not status["enabled"] and saved:
            return {**status, "path": saved, "state": "error", "message": self._unavailable}
        return status

    @Slot(str)
    def chooseVault(self, folder: str) -> None:
        """`FolderDialog` sonucu (`file:///...`) ya da yerel yol. Gecersizse hata bildirilir, onceki ayar korunur."""
        path = Path(QUrl(folder).toLocalFile() or folder)
        try:
            self._sync.set_root(path)
        except VaultUnavailableError as exc:
            self._ctx.notify.error(str(exc))
            return
        if not self._ctx.user_settings.set(SETTING_VAULT_PATH, str(path)):
            self._ctx.notify.error("Vault klasörü ayarı kaydedilemedi.")
        self._unavailable = ""
        if (path / ".obsidian").is_dir():
            self._ctx.notify.info("Obsidian vault'u ayarlandı; notlar yazılıyor.")
        else:
            self._ctx.notify.info("Klasör ayarlandı, ancak içinde '.obsidian' yok: Obsidian'da bu klasörü vault olarak açman gerekir.")
        self.statusChanged.emit()
        self._sync.sync_all()

    @Slot()
    def clearVault(self) -> None:
        """Eşitlemeyi kapatır. Vault'taki mevcut notlara dokunulmaz."""
        self._sync.set_root(None)
        self._ctx.user_settings.set(SETTING_VAULT_PATH, None)
        self._unavailable = ""
        self.statusChanged.emit()

    @Slot()
    def syncNow(self) -> None:
        if not self._sync.status()["enabled"]:
            self._ctx.notify.info("Önce bir Obsidian vault klasörü seç.")
            return
        self._manual_sync = True
        self._sync.sync_all()

    def restore(self) -> None:
        """Uygulama acilisinda kayitli klasoru geri yukler; kullanilamiyorsa nedeni durumda gorunur (ayar silinmez:
        harici disk daha sonra takilabilir). Ilk acilis esitlemesi, eski kayitlarin tasinmasindan sonra yapilir."""
        saved = self._ctx.user_settings.get(SETTING_VAULT_PATH, "")
        if not saved:
            return
        try:
            self._sync.set_root(Path(saved))
        except VaultUnavailableError as exc:
            self._unavailable = str(exc)
            log.warning("Kayitli vault klasoru kullanilamiyor: %s", exc)
            self.statusChanged.emit()
            return
        if not self._startup_hooked:
            self._startup_hooked = True
            self._ctx.pdf_library.legacyAdoptionFinished.connect(lambda _count: self._sync.sync_all())

    def _on_sync_finished(self, report: SyncReport) -> None:
        if not self._manual_sync:
            return
        self._manual_sync = False
        status = self._sync.status()
        (self._ctx.notify.error if report.failed else self._ctx.notify.info)(status["message"])
