"""QML - Python Güncelleme Köprüsü.

Güncelleme denetimi, indirme ilerlemesi, Inno Setup başlatma,
ve Windows Akıllı Uygulama Denetimi (SAC) engelinde otomatik
15 sn x 40 döngü yeniden deneme mantığını yönetir.
"""
from __future__ import annotations

import os
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QCoreApplication, QObject, QThreadPool, QTimer, Signal, Slot

from core.exceptions import InstallerBlockedError, UpdateError
from core.logger import log
from core.paths import update_download_dir
from core.version import __version__
from services.update_service import (
    UpdateInfo,
    UpdateService,
    load_update_settings,
    save_update_settings,
)
from workers.update_worker import CheckUpdateWorker, DownloadWorker


class UpdateBridge(QObject):
    """QML tarafına güncelleme durumlarını ve eylemlerini sunan alt köprü."""

    isCheckingChanged = Signal(bool)
    isDownloadingChanged = Signal(bool)
    downloadProgressChanged = Signal(int)
    updateAvailableChanged = Signal(bool)
    autoCheckEnabledChanged = Signal(bool)
    lastCheckedTextChanged = Signal(str)
    isWaitingWindowsChanged = Signal(bool)
    waitAttemptsLeftChanged = Signal(int)
    isBlockedByWindowsChanged = Signal(bool)
    updateDialogRequested = Signal()
    quitAndInstallRequested = Signal()

    def __init__(self, ctx: Any, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._service = UpdateService()

        self._is_checking = False
        self._is_downloading = False
        self._download_progress = 0
        self._update_available = False
        self._current_update: UpdateInfo | None = None

        self._downloaded_installer: Path | None = None
        self._is_waiting_windows = False
        self._wait_attempts_left = 40
        self._is_blocked_by_windows = False

        self._retry_timer = QTimer(self)
        self._retry_timer.setInterval(15000)  # 15 saniyede bir dene
        self._retry_timer.timeout.connect(self._on_retry_tick)

        settings = load_update_settings()
        self._auto_check_enabled = settings.get("auto_check", True)
        self._last_checked = settings.get("last_checked")

    # ── Properties ─────────────────────────────────────────────────────────────

    @Property(str, constant=True)
    def currentVersion(self) -> str:
        return __version__

    @Property(bool, notify=isCheckingChanged)
    def isChecking(self) -> bool:
        return self._is_checking

    @Property(bool, notify=isDownloadingChanged)
    def isDownloading(self) -> bool:
        return self._is_downloading

    @Property(int, notify=downloadProgressChanged)
    def downloadProgress(self) -> int:
        return self._download_progress

    @Property(bool, notify=updateAvailableChanged)
    def updateAvailable(self) -> bool:
        return self._update_available

    @Property(str, notify=updateAvailableChanged)
    def latestVersion(self) -> str:
        return self._current_update.version if self._current_update else ""

    @Property(str, notify=updateAvailableChanged)
    def releaseNotes(self) -> str:
        return self._current_update.notes if self._current_update else ""

    @Property(str, notify=updateAvailableChanged)
    def downloadSizeMb(self) -> str:
        if not self._current_update or self._current_update.size <= 0:
            return ""
        mb = self._current_update.size / (1024 * 1024)
        return f"{mb:.1f} MB"

    @Property(str, notify=updateAvailableChanged)
    def releaseUrl(self) -> str:
        return self._current_update.html_url if self._current_update else ""

    @Property(bool, notify=autoCheckEnabledChanged)
    def autoCheckEnabled(self) -> bool:
        return self._auto_check_enabled

    @Property(str, notify=lastCheckedTextChanged)
    def lastCheckedText(self) -> str:
        if not self._last_checked:
            return "Henüz denetlenmedi"
        try:
            dt = datetime.fromisoformat(self._last_checked)
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return str(self._last_checked)

    @Property(bool, notify=isWaitingWindowsChanged)
    def isWaitingWindows(self) -> bool:
        return self._is_waiting_windows

    @Property(int, notify=waitAttemptsLeftChanged)
    def waitAttemptsLeft(self) -> int:
        return self._wait_attempts_left

    @Property(bool, notify=isBlockedByWindowsChanged)
    def isBlockedByWindows(self) -> bool:
        return self._is_blocked_by_windows

    # ── Slots ──────────────────────────────────────────────────────────────────

    @Slot()
    def requestUpdateDialog(self) -> None:
        """Güncelleme diyalog penceresini açar."""
        self.updateDialogRequested.emit()

    @Slot()
    def startupCheck(self) -> None:
        """Pencere açıldıktan 3 sn sonra çağrılır: sessiz açılış denetimi."""
        if os.environ.get("PKM_NO_UPDATE_CHECK") == "1":
            return
        if not self._auto_check_enabled:
            return
        self.checkForUpdates(manual=False)

    @Slot()
    @Slot(bool)
    def checkForUpdates(self, manual: bool = True) -> None:
        """GitHub Releases üzerinden yeni sürüm arar."""
        if self._is_checking or self._is_downloading:
            return

        self._is_checking = True
        self.isCheckingChanged.emit(True)

        worker = CheckUpdateWorker(self._service, ignore_skipped=manual)
        worker.signals.finished.connect(lambda info: self._on_check_finished(info, manual))
        worker.signals.failed.connect(lambda err: self._on_check_failed(err, manual))
        QThreadPool.globalInstance().start(worker)

    @Slot()
    def startDownload(self) -> None:
        """Mevcut yeni sürümün kurulum dosyasını indirmeye başlar."""
        if not self._current_update or self._is_downloading:
            return

        self._is_downloading = True
        self._download_progress = 0
        self.isDownloadingChanged.emit(True)
        self.downloadProgressChanged.emit(0)

        worker = DownloadWorker(self._service, self._current_update)
        worker.signals.progress.connect(self._on_download_progress)
        worker.signals.finished.connect(self._on_download_finished)
        worker.signals.failed.connect(self._on_download_failed)
        QThreadPool.globalInstance().start(worker)

    @Slot()
    def skipCurrentVersion(self) -> None:
        """Mevcut sürümü bir sonraki güncellemeye kadar atlar."""
        if self._current_update:
            settings = load_update_settings()
            settings["skipped_version"] = self._current_update.version
            save_update_settings(settings)
            self._update_available = False
            self.updateAvailableChanged.emit(False)
            self._ctx.notify.info(f"v{self._current_update.version} sürümü atlandı.")

    @Slot(bool)
    def setAutoCheckEnabled(self, enabled: bool) -> None:
        """Açılışta otomatik denetleme tercihini kaydeder."""
        if self._auto_check_enabled != enabled:
            self._auto_check_enabled = enabled
            settings = load_update_settings()
            settings["auto_check"] = enabled
            save_update_settings(settings)
            self.autoCheckEnabledChanged.emit(enabled)

    @Slot()
    def resetSkippedVersion(self) -> None:
        """Atlanan sürüm tercihini temizler."""
        settings = load_update_settings()
        settings["skipped_version"] = None
        save_update_settings(settings)
        self._ctx.notify.info("Atlanan sürüm tercihi sıfırlandı.")

    @Slot()
    def cancelWait(self) -> None:
        """Windows bekleme döngüsünü durdurur ve kurulum dosyasını Gezgin'de gösterir."""
        self._retry_timer.stop()
        self._is_waiting_windows = False
        self._is_blocked_by_windows = True
        self.isWaitingWindowsChanged.emit(False)
        self.isBlockedByWindowsChanged.emit(True)
        self.openDownloadFolder()

    @Slot()
    def openReleasePage(self) -> None:
        """GitHub Release sayfasını tarayıcıda açar."""
        url = self.releaseUrl or f"https://github.com/{self._service._repository}/releases"
        webbrowser.open(url)

    @Slot()
    def openDownloadFolder(self) -> None:
        """İndirilen kurulum dosyasını Windows Gezgini'nde seçili gösterir."""
        if self._downloaded_installer and self._downloaded_installer.exists():
            subprocess.run(["explorer.exe", f"/select,{self._downloaded_installer}"])
        else:
            folder = update_download_dir()
            subprocess.run(["explorer.exe", str(folder)])

    # ── Dahili İşleyiciler ─────────────────────────────────────────────────────

    def _on_check_finished(self, info: UpdateInfo | None, manual: bool) -> None:
        self._is_checking = False
        self.isCheckingChanged.emit(False)

        settings = load_update_settings()
        self._last_checked = settings.get("last_checked")
        self.lastCheckedTextChanged.emit(self.lastCheckedText)

        if info:
            self._current_update = info
            self._update_available = True
            self.updateAvailableChanged.emit(True)
            self.updateDialogRequested.emit()
        else:
            self._current_update = None
            self._update_available = False
            self.updateAvailableChanged.emit(False)
            if manual:
                self._ctx.notify.info("Uygulamanız güncel. Yeni bir sürüm bulunamadı.")

    def _on_check_failed(self, error_msg: str, manual: bool) -> None:
        self._is_checking = False
        self.isCheckingChanged.emit(False)
        if manual:
            self._ctx.notify.error(f"Güncelleme denetlenemedi: {error_msg}")

    def _on_download_progress(self, percent: int) -> None:
        self._download_progress = percent
        self.downloadProgressChanged.emit(percent)

    def _on_download_finished(self, installer_path_str: str) -> None:
        self._is_downloading = False
        self.isDownloadingChanged.emit(False)
        self._downloaded_installer = Path(installer_path_str)

        # İndirme tamamlandı; kurulumu başlatmayı dene
        self._try_launch_installer()

    def _on_download_failed(self, error_msg: str) -> None:
        self._is_downloading = False
        self.isDownloadingChanged.emit(False)
        self._ctx.notify.error(f"Güncelleme indirilemedi: {error_msg}")

    def _try_launch_installer(self) -> None:
        if not self._downloaded_installer or not self._downloaded_installer.exists():
            return

        try:
            self._service.launch_installer(self._downloaded_installer)
            # Kurulum başarılı şekilde başlatıldı; uygulamayı kapat
            log.info("Kurulum süreci başlatıldı; uygulama kapatılıyor.")
            self.quitAndInstallRequested.emit()
            QCoreApplication.quit()
        except InstallerBlockedError:
            # SAC engelledi: 15 saniyede bir otomatik deneme başlat
            log.warning("Windows SAC kurulumu engelledi; otomatik yeniden deneme döngüsü başlatılıyor.")
            self._is_waiting_windows = True
            self._wait_attempts_left = 40
            self.isWaitingWindowsChanged.emit(True)
            self.waitAttemptsLeftChanged.emit(40)
            self._retry_timer.start()
        except UpdateError as exc:
            self._ctx.notify.error(str(exc))

    def _on_retry_tick(self) -> None:
        self._wait_attempts_left -= 1
        self.waitAttemptsLeftChanged.emit(self._wait_attempts_left)

        log.info("SAC engelini aşmak için yeniden deneniyor (%d deneme kaldı)...", self._wait_attempts_left)
        try:
            self._service.launch_installer(self._downloaded_installer)
            # Engel kalktı ve başladı!
            self._retry_timer.stop()
            self._is_waiting_windows = False
            self.isWaitingWindowsChanged.emit(False)
            self.quitAndInstallRequested.emit()
            QCoreApplication.quit()
        except InstallerBlockedError:
            if self._wait_attempts_left <= 0:
                self.cancelWait()
        except Exception:
            self.cancelWait()
