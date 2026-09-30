"""`LibraryBridge`'in `core.events.event_bus` aboneligi: kaynak/kategori/etiket degisince liste, cekmece ve
filtreler tazelenir. Ayri bir QObject'tir (kitaplik bridge'inin cocugu) ki yasam suresi bridge'inkine bagli olsun."""
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from core.events import event_bus

if TYPE_CHECKING:
    from ui_qml.bridges.library_bridge import LibraryBridge


class LibraryEventRouter(QObject):
    def __init__(self, library: "LibraryBridge") -> None:
        super().__init__(library)
        self._library = library
        event_bus.resource_added.connect(self._on_resource_changed)
        event_bus.resource_updated.connect(self._on_resource_changed)
        event_bus.resource_deleted.connect(self._on_resource_deleted)
        event_bus.category_updated.connect(self._on_taxonomy_changed)
        event_bus.tag_updated.connect(self._on_taxonomy_changed)
        event_bus.category_deleted.connect(self._on_category_deleted)
        event_bus.tag_deleted.connect(self._on_tag_deleted)

    def _on_resource_changed(self, resource_id: int) -> None:
        if self._library.events_suspended:
            return
        self._library.reload()
        self._library.update_selected_if_matches(resource_id)

    def _on_resource_deleted(self, resource_id: int) -> None:
        self._library.reload()
        if self._library.selectedResource.get("id") == resource_id:
            self._library.closeDrawer()

    def _on_taxonomy_changed(self, _id: int) -> None:
        """Kategori/etiket adi veya rengi degisince liste ve acik cekmece eski adi gostermesin."""
        self._library.reload()
        self._library.update_selected_if_matches()

    def _on_category_deleted(self, category_id: int) -> None:
        if self._library.filters.get("category_id") == category_id:
            self._library.filters["category_id"] = None
        self._on_taxonomy_changed(category_id)

    def _on_tag_deleted(self, tag_id: int) -> None:
        tag_ids = self._library.filters.get("tag_ids")
        if tag_ids and tag_id in tag_ids:
            self._library.filters["tag_ids"] = None
        self._on_taxonomy_changed(tag_id)
