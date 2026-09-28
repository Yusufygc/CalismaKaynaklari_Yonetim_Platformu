from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log
from services.scraper_service import ScraperService


class ScrapeWorkerSignals(QObject):
    finished = Signal(int, dict)


class ScrapeWorker(QRunnable):
    """URL metadata ve OpenGraph verilerini arka plan thread'inde çeker (UI thread'i bloklamaz)."""

    def __init__(self, resource_id: int, url: str) -> None:
        super().__init__()
        self._resource_id = resource_id
        self._url = url
        self.signals = ScrapeWorkerSignals()

    def run(self) -> None:
        try:
            metadata = ScraperService().extract_metadata(self._url)
        except Exception:
            log.exception(
                "Arka planda URL taramasi basarisiz: id=%d url=%s",
                self._resource_id,
                self._url,
            )
            metadata = {}
        self.signals.finished.emit(self._resource_id, metadata)
