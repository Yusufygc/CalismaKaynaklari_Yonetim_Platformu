from PySide6.QtCore import Signal
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from core.events import event_bus
from ui.views.knowledge_pool_view import KnowledgePoolView
from ui.views.reader_view import ReaderView
from ui.views.settings_view import SettingsView
from ui.views.url_showcase_view import UrlShowcaseView

_PAGE_SETTINGS = 0
_PAGE_URL_SHOWCASE = 1
_PAGE_READER = 2
_PAGE_KNOWLEDGE_POOL = 3


class ContentWorkspace(QWidget):
    """Orta panel: SettingsView / UrlShowcaseView arasi filter dispatcher.

    Sidebar'dan gelen filter_key'i ("url_showcase"/"settings") ve FilterBar'dan
    gelen kombinasyonel filtreleri birlestirip controller'a iletir. "Sade Mod"
    acikken UrlShowcaseView tum kaynaklari (URL kisiti yok) duz ResourceCard
    izgarasiyla gosterir; kapaliyken orijinal URL-vitrini davranisina doner.
    """

    add_requested = Signal()

    def __init__(self, controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._active_filters: dict = {}
        self._active_key: str = "url_showcase"
        self._simple_mode: bool = False

        self._build_ui()

        # FilterBar sinyalleri
        self._url_showcase.filters_changed.connect(self._on_filters_changed)

        # Kategori/etiket CRUD sonrasi FilterBar'i yenile
        event_bus.category_added.connect(self._refresh_filter_data)
        event_bus.category_updated.connect(self._refresh_filter_data)
        event_bus.category_deleted.connect(self._refresh_filter_data)
        event_bus.tag_added.connect(self._refresh_filter_data)
        event_bus.tag_updated.connect(self._refresh_filter_data)
        event_bus.tag_deleted.connect(self._refresh_filter_data)
        event_bus.simple_mode_toggled.connect(self._on_simple_mode_changed)

        self._refresh_filter_data()

    # ------------------------------------------------------------------ #
    # Kurulum
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QStackedWidget()
        self._settings_view = SettingsView(self._controller)
        self._url_showcase = UrlShowcaseView()
        self._reader_view = ReaderView()
        self._knowledge_pool = KnowledgePoolView(self._controller)

        self._stack.addWidget(self._settings_view)   # _PAGE_SETTINGS
        self._stack.addWidget(self._url_showcase)    # _PAGE_URL_SHOWCASE
        self._stack.addWidget(self._reader_view)     # _PAGE_READER
        self._stack.addWidget(self._knowledge_pool)  # _PAGE_KNOWLEDGE_POOL

        root.addWidget(self._stack)

        self._url_showcase.add_requested.connect(self.add_requested)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @property
    def reader(self) -> ReaderView:
        return self._reader_view

    @property
    def knowledge_pool(self) -> KnowledgePoolView:
        return self._knowledge_pool

    def apply_filter(self, filter_key: str) -> None:
        # Sidebar geçişi yeni bağlam → FilterBar ve SearchBar resetle.
        self._active_key = filter_key
        self._active_filters = {}
        self._url_showcase.filter_bar.clear(notify=False)
        self._url_showcase.search_bar.clear()

        if filter_key == "settings":
            self._show_settings()
        elif filter_key == "knowledge_pool":
            self._show_knowledge_pool()
        else:
            self._show_url_showcase()

    def refresh(self) -> None:
        current = self._stack.currentIndex()
        if current == _PAGE_SETTINGS:
            self._show_settings()
        elif current == _PAGE_KNOWLEDGE_POOL:
            self._show_knowledge_pool()
        elif current == _PAGE_READER:
            pass  # okuyucu kendi verisini yonetir, kart-gridi yenilemesi gerekmez
        else:
            self._show_url_showcase()

    def show_info_banner(self, message: str) -> None:
        self._url_showcase.show_info_banner(message)

    def show_error_banner(self, message: str) -> None:
        self._url_showcase.show_error_banner(message)

    def open_reader(self, resource) -> None:
        """Filter-dispatch disi, kaynak-ozel sayfa gecisi — geri donuste
        `close_reader()` en son aktif olan filtre sayfasina (`_active_key`) doner."""
        self._reader_view.load_resource(resource)
        self._stack.setCurrentIndex(_PAGE_READER)

    def close_reader(self) -> None:
        self.apply_filter(self._active_key)

    # ------------------------------------------------------------------ #
    # Sayfa gostericiler
    # ------------------------------------------------------------------ #

    def _show_settings(self) -> None:
        self._stack.setCurrentIndex(_PAGE_SETTINGS)
        self._settings_view.load_all()

    def _show_knowledge_pool(self) -> None:
        self._stack.setCurrentIndex(_PAGE_KNOWLEDGE_POOL)
        self._knowledge_pool.load_all()

    def _show_url_showcase(self) -> None:
        self._stack.setCurrentIndex(_PAGE_URL_SHOWCASE)
        filters = {**self._active_filters}
        if not self._simple_mode:
            filters["urls_only"] = True
        resources = self._controller.load_resources_with_filters(filters)
        self._url_showcase.load_resources(resources)

    # ------------------------------------------------------------------ #
    # FilterBar slot'lari
    # ------------------------------------------------------------------ #

    def _on_filters_changed(self, filters: dict) -> None:
        self._active_filters = filters
        self.refresh()

    def _on_simple_mode_changed(self, enabled: bool) -> None:
        self._simple_mode = enabled
        self._url_showcase.set_simple_mode(enabled)
        self.refresh()

    def _refresh_filter_data(self, *_args) -> None:
        categories = self._controller.load_categories()
        tags = self._controller.load_tags()
        self._url_showcase.filter_bar.set_categories(categories)
        self._url_showcase.filter_bar.set_tags(tags)
