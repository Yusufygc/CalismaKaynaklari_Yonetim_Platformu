from PySide6.QtCore import QObject, Signal


class SavedSearchState(QObject):
    """Kayitli aramalarin ortak durumu: liste + su an calistirilan arama.

    Makale aramasi (`MarketBridge`), kaydetme (`MarketSaver`) ve kayitli arama koprusu (`SearchesBridge`) ayni
    durumu okur; boylece birbirlerini dogrudan cagirmadan calisan aramanin koleksiyon etiketini ve "goruldu"
    isaretini paylasirlar.
    """

    listChanged = Signal()
    activeChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.items: list[dict] = []
        self.active_id = 0

    def set_items(self, items: list[dict]) -> None:
        self.items = items
        self.listChanged.emit()

    def set_active(self, search_id: int) -> None:
        if self.active_id != search_id:
            self.active_id = search_id
            self.activeChanged.emit()

    def find(self, search_id: int) -> dict | None:
        return next((s for s in self.items if s["id"] == search_id), None)

    def collection_tag_names(self) -> list[str]:
        """Calisan kayitli aramanin koleksiyon etiketi (yoksa bos liste)."""
        search = self.find(self.active_id)
        return [search["tag"]] if search and search["tag"] else []
