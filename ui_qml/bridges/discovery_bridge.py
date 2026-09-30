from PySide6.QtCore import Property, QObject, Signal, Slot

from core.constants.strings import AppStrings
from ui_qml.bridges.library_bridge import LibraryBridge
from ui_qml.context import BridgeContext
from ui_qml.serializers import annotate_library, serialize_paper
from workers import ReadingSuggestionWorker, RelatedPapersWorker


def _empty_suggestions() -> dict:
    return {"loading": False, "loaded": False, "error": "", "items": [], "sourceCount": 0}


class DiscoveryBridge(QObject):
    """Makale Market kesfi: kart altindaki referans / atif / benzer / yazar listeleri ve kutuphaneden
    "okumadigin" eser onerileri."""

    marketDiscoveryChanged = Signal()
    marketSuggestionsChanged = Signal()

    def __init__(self, ctx: BridgeContext, library: LibraryBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        # Kart altindaki listeler ({"tur:kimlik": durum}) ve "kutuphaneden oneriler".
        self._discovery: dict[str, dict] = {}
        self._suggestions: dict = _empty_suggestions()
        library.resourcesReloaded.connect(self._refresh_library_flags)

    @Property(dict, notify=marketDiscoveryChanged)
    def marketDiscovery(self) -> dict:
        return self._discovery

    @Property(dict, notify=marketSuggestionsChanged)
    def marketSuggestions(self) -> dict:
        return self._suggestions

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
        self._suggestions = {**_empty_suggestions(), "loading": bool(ids), "sourceCount": len(ids)}
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
        """Kaynak eklenip silindikce kesif/oneri listelerindeki "Kutuphanede" durumunu tazeler."""
        groups = (
            ([i for state in self._discovery.values() for i in state["items"]], self.marketDiscoveryChanged),
            (self._suggestions["items"], self.marketSuggestionsChanged),
        )
        if not any(items for items, _signal in groups):
            return
        index = self._ctx.library_index.get()
        for items, signal in groups:
            if annotate_library(items, index):
                signal.emit()
