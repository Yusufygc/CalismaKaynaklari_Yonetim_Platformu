from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log
from services.pdf_download_service import PdfDownloadService


class PdfDownloadWorkerSignals(QObject):
    finished = Signal(int, object)  # resource_id, str (yerel dosya yolu) | None


class PdfDownloadWorker(QRunnable):
    """Web PDF'ini arka plan thread'inde yerel depoya indirir (UI'yi bloklamaz)."""

    def __init__(self, resource_id: int, url: str, dest_dir: Path) -> None:
        super().__init__()
        self._resource_id = resource_id
        self._url = url
        self._dest_dir = dest_dir
        self.signals = PdfDownloadWorkerSignals()

    def run(self) -> None:
        try:
            path = PdfDownloadService().download(self._url, self._dest_dir)
        except Exception:
            log.exception("PDF indirme worker'i basarisiz: id=%d url=%s", self._resource_id, self._url)
            path = None
        self.signals.finished.emit(self._resource_id, str(path) if path else None)
