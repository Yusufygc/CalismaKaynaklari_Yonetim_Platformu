from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log
from services.article_extraction_service import ArticleExtractionService


class ExtractWorkerSignals(QObject):
    finished = Signal(int, object)  # resource_id, str | None


class ExtractWorker(QRunnable):
    """Makalenin zengin HTML tam metnini arka plan thread'inde çeker (UI thread'i bloklamaz)."""

    def __init__(self, resource_id: int, url: str) -> None:
        super().__init__()
        self._resource_id = resource_id
        self._url = url
        self.signals = ExtractWorkerSignals()

    def run(self) -> None:
        try:
            text = ArticleExtractionService().extract_full_text(self._url)
        except Exception:
            log.exception(
                "Arka planda tam metin cikarma basarisiz: id=%d url=%s",
                self._resource_id,
                self._url,
            )
            text = None
        self.signals.finished.emit(self._resource_id, text)
