from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.constants.colors import Colors
from core.constants.strings import AppStrings
from core.events import event_bus
from ui.components.highlight_row import HighlightRow
from ui.components.list_stack import EMPTY_PAGE, GRID_PAGE, add_row, build_list_stack, clear_list
from ui.components.search_bar import SearchBar
from ui.components.vocabulary_row import VocabularyRow
from ui.theme_utils import resolve_theme_color, to_qcolor


class KnowledgePoolView(QFrame):
    """Tum kaynaklardaki alinti/kelimeleri tek yerden listeleyen 'Bilgi Havuzu' sayfasi."""

    resource_jump_requested = Signal(int)

    def __init__(self, controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("KnowledgePoolView")
        self._controller = controller
        self._highlight_rows: dict[int, HighlightRow] = {}
        self._vocabulary_rows: dict[int, VocabularyRow] = {}

        self._build_ui()
        self._connect_events()

    # ------------------------------------------------------------------ #
    # Kurulum
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QLabel(AppStrings.KNOWLEDGE_POOL)
        header.setObjectName("SettingsHeader")
        root.addWidget(header)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("SettingsTabs")
        self._tabs.addTab(self._build_highlights_tab(), AppStrings.KNOWLEDGE_POOL_HIGHLIGHTS_TAB)
        self._tabs.addTab(self._build_vocabulary_tab(), AppStrings.KNOWLEDGE_POOL_VOCAB_TAB)
        root.addWidget(self._tabs, stretch=1)

    def _build_highlights_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(8, 8, 8, 8)

        card, layout = self._build_card()
        self._hl_card_shadow = card.graphicsEffect()
        outer.addWidget(card)

        self._hl_search = SearchBar()
        self._hl_search.search_changed.connect(self._on_hl_search_changed)
        layout.addWidget(self._hl_search)

        self._hl_stack, self._hl_layout = build_list_stack(
            AppStrings.EMPTY_HIGHLIGHTS_MSG, scroll_name="SettingsScrollArea",
        )
        layout.addWidget(self._hl_stack, stretch=1)

        return w

    def _build_vocabulary_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(8, 8, 8, 8)

        card, layout = self._build_card()
        self._vocab_card_shadow = card.graphicsEffect()
        outer.addWidget(card)

        self._vocab_search = SearchBar()
        self._vocab_search.search_changed.connect(self._on_vocab_search_changed)
        layout.addWidget(self._vocab_search)

        self._vocab_stack, self._vocab_layout = build_list_stack(
            AppStrings.EMPTY_VOCAB_MSG, scroll_name="SettingsScrollArea",
        )
        layout.addWidget(self._vocab_stack, stretch=1)

        return w

    @staticmethod
    def _build_card() -> tuple[QFrame, QVBoxLayout]:
        """settings_view.py::_build_card ile ayni gorsel desen (yukseltilmis kart)."""
        card = QFrame()
        card.setObjectName("SettingsListCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 3)
        shadow.setColor(to_qcolor(resolve_theme_color(None, Colors.SHADOW)))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        return card, layout

    # ------------------------------------------------------------------ #
    # Event Bus
    # ------------------------------------------------------------------ #

    def _connect_events(self) -> None:
        event_bus.highlight_added.connect(self._reload_highlights)
        event_bus.highlight_deleted.connect(self._reload_highlights)
        event_bus.vocabulary_added.connect(self._reload_vocabulary)
        event_bus.vocabulary_deleted.connect(self._reload_vocabulary)
        event_bus.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_data: dict) -> None:
        shadow_color = to_qcolor(resolve_theme_color(theme_data, Colors.SHADOW))
        self._hl_card_shadow.setColor(shadow_color)
        self._vocab_card_shadow.setColor(shadow_color)

    # ------------------------------------------------------------------ #
    # Veri yukleme
    # ------------------------------------------------------------------ #

    def load_all(self) -> None:
        self._reload_highlights()
        self._reload_vocabulary()

    def _reload_highlights(self, _id: int = 0) -> None:
        clear_list(self._hl_layout)
        self._highlight_rows.clear()
        items = self._controller.load_all_highlights()
        if not items:
            self._hl_stack.setCurrentIndex(EMPTY_PAGE)
            return
        self._hl_stack.setCurrentIndex(GRID_PAGE)
        for highlight in items:
            title = highlight.resource.title if highlight.resource else None
            row = HighlightRow(highlight, resource_title=title)
            row.delete_requested.connect(self._on_delete_highlight)
            row.resource_clicked.connect(self.resource_jump_requested)
            add_row(self._hl_layout, row)
            self._highlight_rows[highlight.id] = row
        self._on_hl_search_changed(self._hl_search.text())

    def _reload_vocabulary(self, _id: int = 0) -> None:
        clear_list(self._vocab_layout)
        self._vocabulary_rows.clear()
        items = self._controller.load_all_vocabulary()
        if not items:
            self._vocab_stack.setCurrentIndex(EMPTY_PAGE)
            return
        self._vocab_stack.setCurrentIndex(GRID_PAGE)
        for vocabulary in items:
            title = vocabulary.resource.title if vocabulary.resource else None
            row = VocabularyRow(vocabulary, resource_title=title)
            row.delete_requested.connect(self._on_delete_vocabulary)
            row.resource_clicked.connect(self.resource_jump_requested)
            add_row(self._vocab_layout, row)
            self._vocabulary_rows[vocabulary.id] = row
        self._on_vocab_search_changed(self._vocab_search.text())

    # ------------------------------------------------------------------ #
    # Arama
    # ------------------------------------------------------------------ #

    def _on_hl_search_changed(self, text: str) -> None:
        needle = text.strip().lower()
        for row in self._highlight_rows.values():
            row.setVisible(not needle or needle in row.content.lower())

    def _on_vocab_search_changed(self, text: str) -> None:
        needle = text.strip().lower()
        for row in self._vocabulary_rows.values():
            row.setVisible(not needle or needle in row.word.lower())

    # ------------------------------------------------------------------ #
    # Slot'lar
    # ------------------------------------------------------------------ #

    def _on_delete_highlight(self, highlight_id: int) -> None:
        self._controller.delete_highlight(highlight_id)

    def _on_delete_vocabulary(self, vocabulary_id: int) -> None:
        self._controller.delete_vocabulary(vocabulary_id)
