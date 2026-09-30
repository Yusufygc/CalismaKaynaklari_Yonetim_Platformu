from datetime import timedelta

from PySide6.QtCore import Property, QObject, Signal, Slot

from core.constants.strings import AppStrings
from core.events import event_bus
from services.paper_market_service import MarketFilters
from ui_qml.bridges.market_bridge import MarketBridge
from ui_qml.context import BridgeContext
from ui_qml.saved_search_state import SavedSearchState
from workers import SavedSearchCheckWorker

_SAVED_SEARCH_CHECK_INTERVAL = timedelta(hours=1)


def _serialize_saved_search(search) -> dict:
    filters = dict(search.filters or {})
    parts = [search.topic] if search.topic else []
    if filters.get("authorName"):
        parts.append(f"Yazar: {filters['authorName']}")
    return {
        "id": search.id,
        "topic": search.topic,
        "filters": filters,
        "tag": search.tag_name or "",
        "newCount": search.new_count,
        "label": " · ".join(parts) or "Arama",
    }


class SearchesBridge(QObject):
    """Makale Market kayitli aramalari ve yeni yayin takibi. Aramayi `MarketBridge` yurutur; calisan kayitli
    arama durumu `SavedSearchState` uzerinden paylasilir."""

    savedSearchesChanged = Signal()
    activeSavedSearchChanged = Signal()
    savedSearchApplied = Signal(str, "QVariantMap")  # konu, filtreler: QML form alanlarini doldurur

    def __init__(
        self, ctx: BridgeContext, market: MarketBridge, state: SavedSearchState, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._market = market
        self._state = state
        self._checking = False
        state.listChanged.connect(self.savedSearchesChanged)
        state.activeChanged.connect(self.activeSavedSearchChanged)
        event_bus.saved_search_changed.connect(self.reload_saved_searches)

    @Property(list, notify=savedSearchesChanged)
    def savedSearches(self) -> list:
        return self._state.items

    @Property(int, notify=activeSavedSearchChanged)
    def activeSavedSearchId(self) -> int:
        return self._state.active_id

    def refresh(self) -> None:
        self.reload_saved_searches()

    def reload_saved_searches(self) -> None:
        self._state.set_items(
            [_serialize_saved_search(s) for s in self._ctx.controllers.saved_searches.load_saved_searches()]
        )

    @Slot(str, "QVariantMap", str)
    def saveSearch(self, topic: str, filters: dict, tag_name: str) -> None:
        """Gecerli aramayi (konu + filtreler) kaydeder; simdiki ilk sayfa "goruldu" sayilir."""
        search = self._ctx.controllers.saved_searches.create_saved_search(
            topic, filters, tag_name, self._market.recent_paper_ids()
        )
        if search is not None:
            self._state.set_active(search.id)  # Gorunen sonuclar bu aramanin sonuclari
            label = _serialize_saved_search(search)["label"]
            self._ctx.notify.info(AppStrings.NOTIFICATION_SAVED_SEARCH_SAVED_FMT.format(label=label))

    @Slot(int)
    def deleteSavedSearch(self, search_id: int) -> None:
        if self._ctx.controllers.saved_searches.delete_saved_search(search_id) and self._state.active_id == search_id:
            self._state.set_active(0)

    @Slot(int)
    def runSavedSearch(self, search_id: int) -> None:
        """Kayitli aramayi calistirir: QML form alanlari doldurulur, sonuclar "goruldu" isaretlenir ve
        bu arama sirasinda kaydedilen makaleler aramanin koleksiyon etiketini alir."""
        search = self._state.find(search_id)
        if search is None:
            return
        self._state.set_active(search_id)
        self.savedSearchApplied.emit(search["topic"], search["filters"])
        self._market.start_search(search["topic"], MarketFilters.from_dict(search["filters"]))

    @Slot()
    def checkSavedSearches(self) -> None:
        """Son kontrolu 1 saatten eski kayitli aramalarda yeni yayin var mi diye bakar (arka planda)."""
        if self._checking:
            return
        due = [
            {"id": s.id, "topic": s.topic, "filters": dict(s.filters or {}), "seenIds": list(s.seen_ids or [])}
            for s in self._ctx.controllers.saved_searches.load_due_saved_searches(_SAVED_SEARCH_CHECK_INTERVAL)
            if s.id != self._state.active_id
        ]
        if not due:
            return
        self._checking = True
        worker = SavedSearchCheckWorker(due)
        worker.signals.finished.connect(self._on_checked)
        self._ctx.thread_pool.start(worker)

    def _on_checked(self, results: list[dict]) -> None:
        self._checking = False
        for result in results:
            if result["error"]:
                continue  # Ag hatasi: sayac ve "son kontrol" degismez, bir sonraki acilista yeniden denenir.
            self._ctx.controllers.saved_searches.record_saved_search_check(result["id"], result["newCount"])
