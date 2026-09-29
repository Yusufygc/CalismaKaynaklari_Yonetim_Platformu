from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log
from services.paper_market_service import MarketFilters, MarketPage, PaperMarketService


class MarketSearchWorkerSignals(QObject):
    # {sekme: MarketPage}, istek kimligi (arayuz eski/gecersiz sonuclari eleyebilsin)
    finished = Signal(dict, int)


class MarketSearchWorker(QRunnable):
    """Makale Market konu aramasini arka plan thread'inde calistirir (UI thread'i bloklamaz).

    `kind` verilmezse uc sekmenin ilk sayfasi, verilirse yalnizca o sekmenin `page`. sayfasi
    ("Daha fazla yukle") getirilir.
    """

    def __init__(
        self,
        topic: str,
        filters: MarketFilters | None = None,
        kind: str | None = None,
        page: int = 1,
        request_id: int = 0,
    ) -> None:
        super().__init__()
        self._topic = topic
        self._filters = filters
        self._kind = kind
        self._page = page
        self._request_id = request_id
        self.signals = MarketSearchWorkerSignals()

    def run(self) -> None:
        try:
            service = PaperMarketService()
            if self._kind is None:
                results = service.search(self._topic, self._filters)
            else:
                results = {self._kind: service.search_page(self._topic, self._kind, self._filters, self._page)}
        except Exception as exc:
            log.exception("Makale market aramasi basarisiz: konu=%s", self._topic)
            error = str(exc) or exc.__class__.__name__
            kinds = [self._kind] if self._kind else ["recent", "popular", "cited"]
            results = {kind: MarketPage(error=error) for kind in kinds}
        self.signals.finished.emit(results, self._request_id)
