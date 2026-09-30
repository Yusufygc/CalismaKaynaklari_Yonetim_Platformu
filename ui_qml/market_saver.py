"""Makale Market sonuclarini kutuphaneye kaydetme: yinelenen (ayni DOI/OpenAlex kimligi) makaleleri atlar,
calisan kayitli aramanin koleksiyon etiketini ekler ve tek bildirim gonderir."""
from core.constants.strings import AppStrings
from models import ResourceStatus
from ui_qml.bridges.library_bridge import LibraryBridge
from ui_qml.context import BridgeContext
from ui_qml.saved_search_state import SavedSearchState


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


def _message(saved: list, skipped: list, batch: bool) -> str | None:
    if batch:
        if saved and skipped:
            return AppStrings.NOTIFICATION_MARKET_BATCH_SKIPPED_FMT.format(saved=len(saved), skipped=len(skipped))
        if saved:
            return AppStrings.NOTIFICATION_MARKET_BATCH_SAVED_FMT.format(saved=len(saved))
        return AppStrings.NOTIFICATION_MARKET_BATCH_ALL_DUPLICATE if skipped else None
    if saved:
        return AppStrings.NOTIFICATION_MARKET_SAVED_FMT.format(title=saved[0].title)
    if skipped:
        return AppStrings.NOTIFICATION_MARKET_DUPLICATE_FMT.format(title=skipped[0].get("title", ""))
    return None


class MarketSaver:
    def __init__(self, ctx: BridgeContext, library: LibraryBridge, searches: SavedSearchState) -> None:
        self._ctx = ctx
        self._library = library
        self._searches = searches

    def save(self, papers: list[dict], tag_names: list[str] | None = None, batch: bool = False) -> None:
        """Kutuphanede olmayan makaleleri kaydeder; olanlari atlar."""
        index = self._ctx.library_index.get()
        saved, skipped = [], []
        tag_names = [*(tag_names or []), *self._searches.collection_tag_names()]
        with self._library.suspend_events():  # Her kayit icin liste yenilemek yerine sonda bir kez.
            for paper in papers:
                doi, openalex_id = paper.get("doi"), paper.get("openalexId")
                if index.find(doi, openalex_id):
                    skipped.append(paper)
                    continue
                res = self._ctx.controllers.resources.add_resource(_payload(paper, tag_names))
                if res is None:
                    continue  # Hata bildirimi event_bus uzerinden zaten gitti.
                index.add(res.id, doi, openalex_id)
                saved.append(res)
        if saved:
            self._library.reload()
            for res in saved:
                if res.url:
                    self._ctx.extractor.schedule(res.id, res.url)
        message = _message(saved, skipped, batch)
        if message:
            self._ctx.notify.info(message)
