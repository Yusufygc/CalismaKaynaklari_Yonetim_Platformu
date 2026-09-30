from PySide6.QtCore import Property, QObject, Signal, Slot

from core.constants.strings import AppStrings
from services.paper_export_service import PaperExportService
from services.paper_market_service import MARKET_SORTS, MarketFilters, MarketPage
from ui_qml.bridges.library_bridge import LibraryBridge
from ui_qml.context import BridgeContext
from ui_qml.file_export import write_export
from ui_qml.market_saver import MarketSaver
from ui_qml.saved_search_state import SavedSearchState
from ui_qml.serializers import annotate_library, serialize_paper
from workers import MarketSearchWorker

_MARKET_HISTORY_LIMIT = 10


def _blank_meta() -> dict:
    return {"total": 0, "page": 0, "hasMore": False, "error": "", "loadingMore": False}


def _meta_for(page_number: int, page: MarketPage, loaded_count: int) -> dict:
    return {
        "total": page.total,
        "page": page_number,
        "hasMore": not page.error and loaded_count < page.total,
        "error": page.error,
        "loadingMore": False,
    }


class MarketBridge(QObject):
    """Makale Market: OpenAlex aramasi (filtre/sayfalama/gecmis) ve sonuclari kaydetme/disa aktarma.
    Kart kesfi `DiscoveryBridge`'de, kayitli aramalar `SearchesBridge`'dedir."""

    marketResultsChanged = Signal()
    marketSearchLoadingChanged = Signal(bool)
    marketHistoryChanged = Signal()

    def __init__(
        self, ctx: BridgeContext, library: LibraryBridge, searches: SavedSearchState, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._searches = searches
        self._saver = MarketSaver(ctx, library, searches)
        self._results_cache: dict = {kind: [] for kind in MARKET_SORTS}
        self._meta: dict = {kind: _blank_meta() for kind in MARKET_SORTS}
        self._search_loading = False
        # Son arama (sayfalama / "tekrar dene" icin) ve oturum arama gecmisi.
        self._topic = ""
        self._filters = MarketFilters()
        self._request_id = 0
        self._history: list[str] = []

        library.resourcesReloaded.connect(self._refresh_library_flags)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @Property(dict, notify=marketResultsChanged)
    def marketResults(self) -> dict:
        return self._results_cache

    @Property(dict, notify=marketResultsChanged)
    def marketMeta(self) -> dict:
        """Sekme basina {total, page, hasMore, error, loadingMore} (bkz. marketResults)."""
        return self._meta

    @Property(bool, notify=marketSearchLoadingChanged)
    def marketSearchLoading(self) -> bool:
        return self._search_loading

    @Property(list, notify=marketHistoryChanged)
    def marketSearchHistory(self) -> list:
        return self._history

    # ------------------------------------------------------------------ #
    # Arama / sayfalama / gecmis
    # ------------------------------------------------------------------ #

    @Slot(str)
    @Slot(str, "QVariantMap")
    def searchArticles(self, topic: str, filters: dict | None = None) -> None:
        """Konu + filtrelerle yeni arama (uc sekmenin ilk sayfasi). Kullanici elle arama yaptigi
        icin calisan kayitli arama baglami (koleksiyon etiketi, "goruldu" isareti) birakilir."""
        self._searches.set_active(0)
        self.start_search(topic, MarketFilters.from_dict(filters))

    def start_search(self, topic: str, parsed_filters: MarketFilters) -> None:
        """Arama baslatir (kayitli arama kopruleri de kullanir)."""
        topic = topic.strip()
        if not topic and not parsed_filters.author_id:
            return  # Konu ya da yazar filtresi olmadan arama yapilmaz.
        self._topic = topic
        self._filters = parsed_filters
        if topic:
            self._remember_topic(topic)
        self._request_id += 1
        self._search_loading = True
        self.marketSearchLoadingChanged.emit(True)
        worker = MarketSearchWorker(topic, self._filters, request_id=self._request_id)
        worker.signals.finished.connect(self._on_search_finished)
        self._ctx.thread_pool.start(worker)

    @Slot(str)
    def loadMoreArticles(self, kind: str) -> None:
        """Bir sekmenin sonraki sayfasini mevcut listeye ekler."""
        meta = self._meta.get(kind)
        has_query = bool(self._topic or self._filters.author_id)
        if meta is None or not has_query or meta["loadingMore"] or not meta["hasMore"]:
            return
        meta.update(loadingMore=True, error="")
        self.marketResultsChanged.emit()
        worker = MarketSearchWorker(
            self._topic, self._filters, kind=kind, page=meta["page"] + 1, request_id=self._request_id
        )
        worker.signals.finished.connect(self._on_page_loaded)
        self._ctx.thread_pool.start(worker)

    def _on_search_finished(self, results: dict[str, MarketPage], request_id: int) -> None:
        if request_id != self._request_id:
            return  # Kullanici bu arada yeni bir arama baslatti.
        self._results_cache = {kind: [serialize_paper(p) for p in page.items] for kind, page in results.items()}
        annotate_library(
            [i for items in self._results_cache.values() for i in items], self._ctx.library_index.get()
        )
        self._meta = {kind: _meta_for(1, page, len(page.items)) for kind, page in results.items()}
        self._search_loading = False
        self.marketSearchLoadingChanged.emit(False)
        self.marketResultsChanged.emit()
        if self._searches.active_id:
            self._ctx.controllers.saved_searches.mark_saved_search_seen(
                self._searches.active_id, self.recent_paper_ids()
            )

    def recent_paper_ids(self) -> list[str]:
        """"En guncel" sekmesindeki (goruldu isaretlenecek) makalelerin OpenAlex kimlikleri."""
        return [i["openalexId"] for i in self._results_cache.get("recent", []) if i["openalexId"]]

    def _on_page_loaded(self, results: dict[str, MarketPage], request_id: int) -> None:
        if request_id != self._request_id:
            return
        for kind, page in results.items():
            meta = self._meta.get(kind)
            if meta is None:
                continue
            if page.error:
                # Mevcut liste korunur; yalnizca "yuklenemedi" bilgisi gosterilir.
                meta.update(loadingMore=False, error=page.error)
                continue
            new_items = [serialize_paper(p) for p in page.items]
            annotate_library(new_items, self._ctx.library_index.get())
            merged = self._results_cache.get(kind, []) + new_items
            self._results_cache[kind] = merged
            self._meta[kind] = _meta_for(meta["page"] + 1, page, len(merged))
        self.marketResultsChanged.emit()

    @Slot()
    def resetMarketResults(self) -> None:
        """Sonuclari temizler (ornegin yazar filtresi kaldirilip konu da bossa)."""
        self._request_id += 1  # Gecikmis yanitlar atilsin.
        self._searches.set_active(0)
        self._results_cache = {kind: [] for kind in MARKET_SORTS}
        self._meta = {kind: _blank_meta() for kind in MARKET_SORTS}
        self._topic = ""
        self._filters = MarketFilters()
        self._search_loading = False
        self.marketSearchLoadingChanged.emit(False)
        self.marketResultsChanged.emit()

    @Slot()
    def clearMarketHistory(self) -> None:
        self._history = []
        self.marketHistoryChanged.emit()

    def _remember_topic(self, topic: str) -> None:
        history = [t for t in self._history if t.lower() != topic.lower()]
        self._history = [topic, *history][:_MARKET_HISTORY_LIMIT]
        self.marketHistoryChanged.emit()

    def _refresh_library_flags(self) -> None:
        """Kaynak eklenip silindikce Market sonuclarindaki "Kutuphanede" durumunu tazeler."""
        items = [i for group in self._results_cache.values() for i in group]
        if items and annotate_library(items, self._ctx.library_index.get()):
            self.marketResultsChanged.emit()

    # ------------------------------------------------------------------ #
    # Kaydetme / disa aktarma
    # ------------------------------------------------------------------ #

    @Slot(dict)
    def saveMarketResult(self, paper: dict) -> None:
        """Makale Market sonucunu kaynak olarak kaydeder (bkz. `MarketSaver`)."""
        self._saver.save([paper])

    @Slot(dict)
    def saveMarketResultForLater(self, paper: dict) -> None:
        """"Sonra oku": kaydeder ve `okuma-listesi` etiketiyle isaretler."""
        self._saver.save([paper], tag_names=[AppStrings.MARKET_READ_LATER_TAG])

    @Slot("QVariantList")
    def saveMarketResults(self, papers: list) -> None:
        """Secili sonuclari toplu kaydeder (tek yenileme, tek bildirim)."""
        self._saver.save(papers, batch=True)

    @Slot(str, str, "QVariantList")
    def exportMarketResults(self, kind: str, file_url: str, papers: list) -> None:
        """Market sonuclarini BibTeX (.bib) ya da CSV (.csv) olarak dosyaya yazar."""
        if not papers:
            self._ctx.notify.info(AppStrings.NOTIFICATION_MARKET_EXPORT_EMPTY)
            return
        if kind == "bibtex":
            write_export(file_url, PaperExportService.bibtex(papers), self._ctx.notify, ".bib")
        elif kind == "csv":
            write_export(file_url, PaperExportService.csv(papers), self._ctx.notify, ".csv", encoding="utf-8-sig")
        else:
            raise ValueError(f"Gecersiz disa aktarim turu: {kind}")
