from datetime import timedelta

from PySide6.QtCore import Property, QObject, Signal, Slot

from core.constants.strings import AppStrings
from core.events import event_bus
from models import ResourceStatus
from services.paper_export_service import PaperExportService
from services.paper_market_service import MARKET_SORTS, MarketFilters, MarketPage
from ui_qml.bridges.library_bridge import LibraryBridge
from ui_qml.context import BridgeContext
from ui_qml.file_export import write_export
from ui_qml.serializers import annotate_library, serialize_paper
from workers import MarketSearchWorker, ReadingSuggestionWorker, RelatedPapersWorker, SavedSearchCheckWorker

_MARKET_HISTORY_LIMIT = 10
_SAVED_SEARCH_CHECK_INTERVAL = timedelta(hours=1)


class MarketBridge(QObject):
    """Makale Market: OpenAlex aramasi (filtre/sayfalama/gecmis), kart kesfi (referans/atif/benzer/yazar),
    kutuphaneden okuma onerileri, toplu kaydetme/disa aktarma ve kayitli aramalar (yeni yayin takibi)."""

    marketResultsChanged = Signal()
    marketSearchLoadingChanged = Signal(bool)
    marketHistoryChanged = Signal()
    marketDiscoveryChanged = Signal()
    marketSuggestionsChanged = Signal()
    savedSearchesChanged = Signal()
    activeSavedSearchChanged = Signal()
    savedSearchApplied = Signal(str, "QVariantMap")  # konu, filtreler: QML form alanlarini doldurur

    def __init__(self, ctx: BridgeContext, library: LibraryBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._library = library
        self._results_cache: dict = {kind: [] for kind in MARKET_SORTS}
        self._meta: dict = {kind: self._blank_meta() for kind in MARKET_SORTS}
        self._search_loading = False
        # Son arama (sayfalama / "tekrar dene" icin) ve oturum arama gecmisi.
        self._topic = ""
        self._filters = MarketFilters()
        self._request_id = 0
        self._history: list[str] = []
        # Kart altindaki "referanslar / atif yapanlar / benzer / yazar" listeleri ({"tur:kimlik": durum})
        # ve "kutuphaneden oneriler".
        self._discovery: dict[str, dict] = {}
        self._suggestions: dict = self._empty_suggestions()
        # Kayitli aramalar; calistirilan kayitli arama (yeni yayin sayaci ve koleksiyon etiketi icin).
        self._saved_searches_cache: list[dict] = []
        self._active_saved_search_id = 0
        self._saved_searches_checking = False

        library.resourcesReloaded.connect(self._refresh_library_flags)
        event_bus.saved_search_changed.connect(self.reload_saved_searches)

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

    @Property(dict, notify=marketDiscoveryChanged)
    def marketDiscovery(self) -> dict:
        return self._discovery

    @Property(dict, notify=marketSuggestionsChanged)
    def marketSuggestions(self) -> dict:
        return self._suggestions

    @Property(list, notify=marketHistoryChanged)
    def marketSearchHistory(self) -> list:
        return self._history

    @Property(list, notify=savedSearchesChanged)
    def savedSearches(self) -> list:
        return self._saved_searches_cache

    @Property(int, notify=activeSavedSearchChanged)
    def activeSavedSearchId(self) -> int:
        return self._active_saved_search_id

    def refresh(self) -> None:
        self.reload_saved_searches()

    # ------------------------------------------------------------------ #
    # Arama / sayfalama / gecmis
    # ------------------------------------------------------------------ #

    @staticmethod
    def _blank_meta() -> dict:
        return {"total": 0, "page": 0, "hasMore": False, "error": "", "loadingMore": False}

    @Slot(str)
    @Slot(str, "QVariantMap")
    def searchArticles(self, topic: str, filters: dict | None = None) -> None:
        """Konu + filtrelerle yeni arama (uc sekmenin ilk sayfasi). Kullanici elle arama yaptigi
        icin calisan kayitli arama baglami (koleksiyon etiketi, "goruldu" isareti) birakilir."""
        self._set_active_saved_search(0)
        self._start_search(topic, MarketFilters.from_dict(filters))

    def _start_search(self, topic: str, parsed_filters: MarketFilters) -> None:
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

    @staticmethod
    def _meta_for(page_number: int, page: MarketPage, loaded_count: int) -> dict:
        return {
            "total": page.total,
            "page": page_number,
            "hasMore": not page.error and loaded_count < page.total,
            "error": page.error,
            "loadingMore": False,
        }

    def _on_search_finished(self, results: dict[str, MarketPage], request_id: int) -> None:
        if request_id != self._request_id:
            return  # Kullanici bu arada yeni bir arama baslatti.
        self._results_cache = {kind: [serialize_paper(p) for p in page.items] for kind, page in results.items()}
        annotate_library(
            [i for items in self._results_cache.values() for i in items], self._ctx.library_index.get()
        )
        self._meta = {kind: self._meta_for(1, page, len(page.items)) for kind, page in results.items()}
        self._search_loading = False
        self.marketSearchLoadingChanged.emit(False)
        self.marketResultsChanged.emit()
        if self._active_saved_search_id:
            recent_ids = [i["openalexId"] for i in self._results_cache.get("recent", []) if i["openalexId"]]
            self._ctx.controllers.saved_searches.mark_saved_search_seen(self._active_saved_search_id, recent_ids)

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
            self._meta[kind] = self._meta_for(meta["page"] + 1, page, len(merged))
        self.marketResultsChanged.emit()

    @Slot()
    def resetMarketResults(self) -> None:
        """Sonuclari temizler (ornegin yazar filtresi kaldirilip konu da bossa)."""
        self._request_id += 1  # Gecikmis yanitlar atilsin.
        self._set_active_saved_search(0)
        self._results_cache = {kind: [] for kind in MARKET_SORTS}
        self._meta = {kind: self._blank_meta() for kind in MARKET_SORTS}
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

    # ------------------------------------------------------------------ #
    # Kesif (referans / atif / benzer / yazar) ve oneriler
    # ------------------------------------------------------------------ #

    @staticmethod
    def _empty_suggestions() -> dict:
        return {"loading": False, "loaded": False, "error": "", "items": [], "sourceCount": 0}

    @Slot(str, str)
    def loadDiscovery(self, kind: str, openalex_id: str) -> None:
        """Bir Market kartinin altindaki listeyi (references / citations / similar / author) yukler."""
        key = f"{kind}:{openalex_id}"
        state = self._discovery.get(key, {})
        if not openalex_id or state.get("loaded") or state.get("loading"):
            return
        self._discovery[key] = {"loading": True, "loaded": False, "error": "", "items": []}
        self.marketDiscoveryChanged.emit()
        worker = RelatedPapersWorker(openalex_id, kind)
        worker.signals.finished.connect(self._on_discovery_finished)
        self._ctx.thread_pool.start(worker)

    def _on_discovery_finished(self, openalex_id: str, kind: str, papers, error: str) -> None:
        items = [serialize_paper(p) for p in papers]
        if items:
            annotate_library(items, self._ctx.library_index.get())
        self._discovery[f"{kind}:{openalex_id}"] = {
            "loading": False,
            "loaded": not error,
            "error": AppStrings.RELATED_PAPERS_LOAD_FAILED if error else "",
            "items": items,
        }
        self.marketDiscoveryChanged.emit()

    @Slot()
    def loadLibrarySuggestions(self) -> None:
        """Kutuphanedeki makalelerin ortak referanslarindan "okumadigin" eser onerileri."""
        if self._suggestions["loading"]:
            return
        ids = [
            (r.extra_metadata or {}).get("openalex_id")
            for r in self._ctx.controllers.resources.load_resources_with_filters({})
        ]
        ids = [i for i in ids if i]
        self._suggestions = {**self._empty_suggestions(), "loading": bool(ids), "sourceCount": len(ids)}
        self.marketSuggestionsChanged.emit()
        if not ids:
            return
        worker = ReadingSuggestionWorker(ids)
        worker.signals.finished.connect(self._on_suggestions_finished)
        self._ctx.thread_pool.start(worker)

    def _on_suggestions_finished(self, suggestions, error: str) -> None:
        items = []
        for suggestion in suggestions:
            item = serialize_paper(suggestion.paper)
            item["citedByLibrary"] = suggestion.cited_by_library
            items.append(item)
        if items:
            annotate_library(items, self._ctx.library_index.get())
        self._suggestions = {
            "loading": False,
            "loaded": not error,
            "error": AppStrings.RELATED_PAPERS_LOAD_FAILED if error else "",
            "items": items,
            "sourceCount": self._suggestions["sourceCount"],
        }
        self.marketSuggestionsChanged.emit()

    def _refresh_library_flags(self) -> None:
        """Kaynak eklenip silindikce Market sonuclarindaki "Kutuphanede" durumunu tazeler."""
        groups = (
            ([i for items in self._results_cache.values() for i in items], self.marketResultsChanged),
            ([i for state in self._discovery.values() for i in state["items"]], self.marketDiscoveryChanged),
            (self._suggestions["items"], self.marketSuggestionsChanged),
        )
        if not any(items for items, _signal in groups):
            return
        index = self._ctx.library_index.get()
        for items, signal in groups:
            if annotate_library(items, index):
                signal.emit()

    # ------------------------------------------------------------------ #
    # Kayitli aramalar ve yeni yayin takibi
    # ------------------------------------------------------------------ #

    def reload_saved_searches(self) -> None:
        self._saved_searches_cache = [
            self._serialize_saved_search(s) for s in self._ctx.controllers.saved_searches.load_saved_searches()
        ]
        self.savedSearchesChanged.emit()

    @staticmethod
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

    @Slot(str, "QVariantMap", str)
    def saveSearch(self, topic: str, filters: dict, tag_name: str) -> None:
        """Gecerli aramayi (konu + filtreler) kaydeder; simdiki ilk sayfa "goruldu" sayilir."""
        seen_ids = [i["openalexId"] for i in self._results_cache.get("recent", []) if i["openalexId"]]
        search = self._ctx.controllers.saved_searches.create_saved_search(topic, filters, tag_name, seen_ids)
        if search is not None:
            self._set_active_saved_search(search.id)  # Gorunen sonuclar bu aramanin sonuclari
            label = self._serialize_saved_search(search)["label"]
            self._ctx.notify.info(AppStrings.NOTIFICATION_SAVED_SEARCH_SAVED_FMT.format(label=label))

    @Slot(int)
    def deleteSavedSearch(self, search_id: int) -> None:
        if self._ctx.controllers.saved_searches.delete_saved_search(search_id) and self._active_saved_search_id == search_id:
            self._set_active_saved_search(0)

    @Slot(int)
    def runSavedSearch(self, search_id: int) -> None:
        """Kayitli aramayi calistirir: QML form alanlari doldurulur, sonuclar "goruldu" isaretlenir ve
        bu arama sirasinda kaydedilen makaleler aramanin koleksiyon etiketini alir."""
        search = next((s for s in self._saved_searches_cache if s["id"] == search_id), None)
        if search is None:
            return
        self._set_active_saved_search(search_id)
        self.savedSearchApplied.emit(search["topic"], search["filters"])
        self._start_search(search["topic"], MarketFilters.from_dict(search["filters"]))

    @Slot()
    def checkSavedSearches(self) -> None:
        """Son kontrolu 1 saatten eski kayitli aramalarda yeni yayin var mi diye bakar (arka planda)."""
        if self._saved_searches_checking:
            return
        due = [
            {"id": s.id, "topic": s.topic, "filters": dict(s.filters or {}), "seenIds": list(s.seen_ids or [])}
            for s in self._ctx.controllers.saved_searches.load_due_saved_searches(_SAVED_SEARCH_CHECK_INTERVAL)
            if s.id != self._active_saved_search_id
        ]
        if not due:
            return
        self._saved_searches_checking = True
        worker = SavedSearchCheckWorker(due)
        worker.signals.finished.connect(self._on_saved_searches_checked)
        self._ctx.thread_pool.start(worker)

    def _on_saved_searches_checked(self, results: list[dict]) -> None:
        self._saved_searches_checking = False
        for result in results:
            if result["error"]:
                continue  # Ag hatasi: sayac ve "son kontrol" degismez, bir sonraki acilista yeniden denenir.
            self._ctx.controllers.saved_searches.record_saved_search_check(result["id"], result["newCount"])

    def _set_active_saved_search(self, search_id: int) -> None:
        if self._active_saved_search_id != search_id:
            self._active_saved_search_id = search_id
            self.activeSavedSearchChanged.emit()

    def _collection_tag_names(self) -> list[str]:
        search = next((s for s in self._saved_searches_cache if s["id"] == self._active_saved_search_id), None)
        return [search["tag"]] if search and search["tag"] else []

    # ------------------------------------------------------------------ #
    # Kaydetme / disa aktarma
    # ------------------------------------------------------------------ #

    @Slot(dict)
    def saveMarketResult(self, paper: dict) -> None:
        """Makale Market sonucunu kaynak olarak kaydeder (bkz. `_save_papers`)."""
        self._save_papers([paper])

    @Slot(dict)
    def saveMarketResultForLater(self, paper: dict) -> None:
        """"Sonra oku": kaydeder ve `okuma-listesi` etiketiyle isaretler."""
        self._save_papers([paper], tag_names=[AppStrings.MARKET_READ_LATER_TAG])

    @Slot("QVariantList")
    def saveMarketResults(self, papers: list) -> None:
        """Secili sonuclari toplu kaydeder (tek yenileme, tek bildirim)."""
        self._save_papers(papers, batch=True)

    @staticmethod
    def _payload(paper: dict, tag_names: list[str]) -> dict:
        """Market sonucu icin daraltilmis `saveResource` yuku: kategori yok, yazar/yil/atif sayisi
        `extra_metadata`'ya yazilir (formda hic olmayan bir alan)."""
        return {
            "title": (paper.get("title") or "").strip() or "(Baslik yok)",
            "url": paper.get("url") or None,
            "category_id": None,
            "status": ResourceStatus.INBOX,
            "priority": 2,
            "content": None,
            "tag_names": list(tag_names),
            "extra_metadata": {
                key: value
                for key, value in {
                    "authors": paper.get("authors", []),
                    "year": paper.get("year"),
                    "citation_count": paper.get("citationCount", 0),
                    "venue": paper.get("venue"),
                    "doi": paper.get("doi"),
                    "openalex_id": paper.get("openalexId"),
                    "source": "openalex",
                }.items()
                if value not in (None, "", [])
            },
        }

    def _save_papers(self, papers: list[dict], tag_names: list[str] | None = None, batch: bool = False) -> None:
        """Kutuphanede olmayan makaleleri kaydeder; olanlari atlar (ayni DOI/OpenAlex kimligi)."""
        index = self._ctx.library_index.get()
        saved, skipped = [], []
        tag_names = [*(tag_names or []), *self._collection_tag_names()]
        with self._library.suspend_events():  # Her kayit icin liste yenilemek yerine sonda bir kez.
            for paper in papers:
                doi, openalex_id = paper.get("doi"), paper.get("openalexId")
                if index.find(doi, openalex_id):
                    skipped.append(paper)
                    continue
                res = self._ctx.controllers.resources.add_resource(self._payload(paper, tag_names))
                if res is None:
                    continue  # Hata bildirimi event_bus uzerinden zaten gitti.
                index.add(res.id, doi, openalex_id)
                saved.append(res)
        if saved:
            self._library.reload()
            for res in saved:
                if res.url:
                    self._ctx.extractor.schedule(res.id, res.url)
        self._notify_save(saved, skipped, batch)

    def _notify_save(self, saved: list, skipped: list, batch: bool) -> None:
        if batch:
            if saved and skipped:
                message = AppStrings.NOTIFICATION_MARKET_BATCH_SKIPPED_FMT.format(saved=len(saved), skipped=len(skipped))
            elif saved:
                message = AppStrings.NOTIFICATION_MARKET_BATCH_SAVED_FMT.format(saved=len(saved))
            elif skipped:
                message = AppStrings.NOTIFICATION_MARKET_BATCH_ALL_DUPLICATE
            else:
                return
        elif saved:
            message = AppStrings.NOTIFICATION_MARKET_SAVED_FMT.format(title=saved[0].title)
        elif skipped:
            message = AppStrings.NOTIFICATION_MARKET_DUPLICATE_FMT.format(title=skipped[0].get("title", ""))
        else:
            return
        self._ctx.notify.info(message)

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
