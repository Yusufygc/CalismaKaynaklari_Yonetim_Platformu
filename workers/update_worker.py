"""Güncelleme denetimi ve indirme işlemlerini arka planda yürüten worker'lar."""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log
from services.update_service import UpdateInfo, UpdateService


class CheckUpdateWorkerSignals(QObject):
    finished = Signal(object)  # UpdateInfo | None
    failed = Signal(str)


class CheckUpdateWorker(QRunnable):
    """GitHub Releases üzerinden yeni sürüm denetimini arka planda yapar."""

    def __init__(self, service: UpdateService, ignore_skipped: bool = False) -> None:
        super().__init__()
        self._service = service
        self._ignore_skipped = ignore_skipped
        self.signals = CheckUpdateWorkerSignals()

    def run(self) -> None:
        try:
            info = self._service.check_for_update(ignore_skipped=self._ignore_skipped)
            self.signals.finished.emit(info)
        except Exception as exc:
            log.warning("Güncelleme denetimi hatası: %s", exc)
            self.signals.failed.emit(str(exc))


class DownloadWorkerSignals(QObject):
    progress = Signal(int)
    finished = Signal(str)  # installer_path
    failed = Signal(str)


class DownloadWorker(QRunnable):
    """Kurulum dosyasını arka planda indirir ve SHA-256 doğrulamasını yapar."""

    def __init__(self, service: UpdateService, info: UpdateInfo) -> None:
        super().__init__()
        self._service = service
        self._info = info
        self.signals = DownloadWorkerSignals()

    def run(self) -> None:
        try:
            installer_path = self._service.download_installer(
                self._info,
                progress_callback=self.signals.progress.emit,
            )
            self.signals.finished.emit(str(installer_path))
        except Exception as exc:
            log.error("Kurulum dosyası indirme hatası: %s", exc)
            self.signals.failed.emit(str(exc))
