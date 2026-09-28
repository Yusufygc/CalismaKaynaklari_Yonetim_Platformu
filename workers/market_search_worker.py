from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log
from services.paper_market_service import PaperMarketService


class MarketSearchWorkerSignals(QObject):
    finished = Signal(dict)  # {"recent": [PaperResult], "popular": [...], "cited": [...]}


class MarketSearchWorker(QRunnable):
    """Makale Market konu aramasini arka plan thread'inde calistirir (UI thread'i bloklamaz)."""

    def __init__(self, topic: str) -> None:
        super().__init__()
        self._topic = topic
        self.signals = MarketSearchWorkerSignals()

    def run(self) -> None:
        try:
            results = PaperMarketService().search(self._topic)
        except Exception:
            log.exception("Makale market aramasi basarisiz: konu=%s", self._topic)
            results = {"recent": [], "popular": [], "cited": []}
        self.signals.finished.emit(results)
