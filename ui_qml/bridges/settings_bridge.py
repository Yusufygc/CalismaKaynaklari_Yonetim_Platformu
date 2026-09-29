from PySide6.QtCore import Property, QObject, Signal, Slot

from core.constants.strings import AppStrings
from ui_qml.context import BridgeContext

_DEFAULT_CATEGORY_COLOR = "#64748B"


class SettingsBridge(QObject):
    """Ayarlar sayfasi: kategori ve etiket yonetimi.

    Kategori/etiket degisince acik kaynak listesi/cekmece/okuyucu tazelemesi bu sinifin isi degildir:
    controller'in yayimladigi `category_*` / `tag_*` olaylarini `LibraryBridge` ve `ReaderBridge` dinler.
    """

    categoriesChanged = Signal()
    tagsChanged = Signal()

    def __init__(self, ctx: BridgeContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._categories_cache: list[dict] = []
        self._tags_cache: list[dict] = []

    @Property(list, notify=categoriesChanged)
    def categories(self) -> list:
        return self._categories_cache

    @Property(list, notify=tagsChanged)
    def tags(self) -> list:
        return self._tags_cache

    def refresh(self) -> None:
        self.reload_categories()
        self.reload_tags()

    def reload_categories(self) -> None:
        self._categories_cache = [
            {
                "id": c.id,
                "name": c.name,
                "color_hex": c.color_hex or _DEFAULT_CATEGORY_COLOR,
                "icon": c.icon or "",
                "resource_count": len(c.resources) if hasattr(c, "resources") else 0,
            }
            for c in self._ctx.controllers.categories.load_categories()
        ]
        self.categoriesChanged.emit()

    def reload_tags(self) -> None:
        self._tags_cache = [
            {
                "id": t.id,
                "name": t.name,
                "resource_count": len(t.resources) if hasattr(t, "resources") else 0,
            }
            for t in self._ctx.controllers.tags.load_tags()
        ]
        self.tagsChanged.emit()

    # ------------------------------------------------------------------ #
    # Kategori
    # ------------------------------------------------------------------ #

    @Slot(str, str, str)
    def createCategory(self, name: str, color_hex: str, icon: str = "") -> None:
        if not name.strip():
            return
        result = self._ctx.controllers.categories.create_category(
            name.strip(), color_hex.strip() or _DEFAULT_CATEGORY_COLOR, icon.strip()
        )
        if result is None:
            return
        self.reload_categories()
        self._ctx.notify.info(AppStrings.NOTIFICATION_CATEGORY_ADDED_FMT.format(name=name))

    @Slot(int, str, str, str)
    def updateCategory(self, category_id: int, name: str, color_hex: str, icon: str = "") -> None:
        if not name.strip():
            return
        result = self._ctx.controllers.categories.update_category(
            category_id, name.strip(), color_hex.strip(), icon.strip()
        )
        if result is None:
            return
        self.reload_categories()
        self._ctx.notify.info(AppStrings.NOTIFICATION_CATEGORY_UPDATED)

    @Slot(int)
    def deleteCategory(self, category_id: int) -> None:
        if not self._ctx.controllers.categories.delete_category(category_id):
            return
        self.reload_categories()
        self._ctx.notify.info(AppStrings.NOTIFICATION_CATEGORY_DELETED)

    # ------------------------------------------------------------------ #
    # Etiket
    # ------------------------------------------------------------------ #

    @Slot(str)
    def createTag(self, name: str) -> None:
        if not name.strip():
            return
        if self._ctx.controllers.tags.create_tag(name.strip()) is None:
            return
        self.reload_tags()
        self._ctx.notify.info(AppStrings.NOTIFICATION_TAG_ADDED_FMT.format(name=name))

    @Slot(int, str)
    def updateTag(self, tag_id: int, new_name: str) -> None:
        if not new_name.strip():
            return
        if self._ctx.controllers.tags.update_tag(tag_id, new_name.strip()) is None:
            return
        self.reload_tags()
        self._ctx.notify.info(AppStrings.NOTIFICATION_TAG_UPDATED)

    @Slot(int)
    def deleteTag(self, tag_id: int) -> None:
        if not self._ctx.controllers.tags.delete_tag(tag_id):
            return
        self.reload_tags()
        self._ctx.notify.info(AppStrings.NOTIFICATION_TAG_DELETED)
