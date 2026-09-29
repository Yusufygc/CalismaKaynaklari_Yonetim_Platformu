from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log
from services.paper_market_service import MarketFilters, PaperMarketService


class SavedSearchCheckWorkerSignals(QObject):
    # [{"id": int, "newCount": int, "error": str}] -- her kayitli arama icin bir girdi
    finished = Signal(object)


class SavedSearchCheckWorker(QRunnable):
    """Kayitli aramalarin "en guncel" ilk sayfasini cekip gorulmemis (seen_ids disinda) yayinlari sayar."""

    def __init__(self, searches: list[dict]) -> None:
        super().__init__()
        self._searches = searches
        self.signals = SavedSearchCheckWorkerSignals()

    def run(self) -> None:
        service = PaperMarketService()
        results = []
        for search in self._searches:
            page = service.search_page(search["topic"], "recent", MarketFilters.from_dict(search["filters"]))
            if page.error:
                log.warning("Kayitli arama kontrolu basarisiz: id=%s - %s", search["id"], page.error)
                results.append({"id": search["id"], "newCount": 0, "error": page.error})
                continue
            seen = set(search["seenIds"])
            new_count = sum(1 for p in page.items if p.openalex_id and p.openalex_id not in seen)
            results.append({"id": search["id"], "newCount": new_count, "error": ""})
        self.signals.finished.emit(results)
