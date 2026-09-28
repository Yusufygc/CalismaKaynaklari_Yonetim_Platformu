from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.constants.colors import Colors
from core.constants.strings import AppStrings
from core.events import event_bus
from ui.components.category_row import CategoryRow
from ui.components.color_picker_button import ColorPickerButton
from ui.components.flow_layout import build_flow_stack, clear_flow, EMPTY_PAGE, GRID_PAGE
from ui.components.inline_banner import InlineBanner
from ui.components.search_bar import SearchBar
from ui.components.tag_row import TagRow
from ui.theme_utils import resolve_theme_color, to_qcolor


class SettingsView(QFrame):
    """Ayarlar sayfasi: Kategoriler ve Etiketler CRUD."""

    def __init__(self, controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsView")
        self._controller = controller
        self._category_rows: dict[int, CategoryRow] = {}
        self._tag_rows: dict[int, TagRow] = {}

        self._build_ui()
        self._connect_events()

    # ------------------------------------------------------------------ #
    # Kurulum
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QLabel(AppStrings.SETTINGS)
        header.setObjectName("SettingsHeader")
        root.addWidget(header)

        self._banner = InlineBanner()
        root.addWidget(self._banner)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("SettingsTabs")

        self._tabs.addTab(self._build_category_tab(), AppStrings.SETTINGS_CATEGORIES_TAB)
        self._tabs.addTab(self._build_tag_tab(), AppStrings.SETTINGS_TAGS_TAB)

        root.addWidget(self._tabs, stretch=1)

    def _build_category_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(8, 8, 8, 8)

        card, layout = self._build_card()
        self._cat_card_shadow = card.graphicsEffect()
        outer.addWidget(card)

        self._cat_search = SearchBar()
        self._cat_search.search_changed.connect(self._on_cat_search_changed)
        layout.addWidget(self._cat_search)

        self._cat_stack, self._cat_flow = build_flow_stack(
            AppStrings.EMPTY_CATEGORIES_MSG,
            h_spacing=8, v_spacing=8,
            scroll_name="SettingsScrollArea",
        )
        layout.addWidget(self._cat_stack, stretch=1)
        layout.addWidget(self._card_separator())

        # Yeni kategori ekleme formu
        add_row = QHBoxLayout()
        add_row.setSpacing(6)

        self._cat_name_input = QLineEdit()
        self._cat_name_input.setObjectName("FormField")
        self._cat_name_input.setPlaceholderText(AppStrings.CATEGORY_NAME)
        add_row.addWidget(self._cat_name_input, stretch=2)

        self._cat_color_picker = ColorPickerButton()
        self._cat_color_picker.setFixedWidth(140)
        self._cat_color_picker.setToolTip(AppStrings.CATEGORY_COLOR)
        add_row.addWidget(self._cat_color_picker)

        self._cat_icon_input = QLineEdit()
        self._cat_icon_input.setObjectName("FormField")
        self._cat_icon_input.setPlaceholderText(AppStrings.CATEGORY_ICON)
        self._cat_icon_input.setFixedWidth(120)
        add_row.addWidget(self._cat_icon_input)

        self._cat_add_btn = QPushButton(AppStrings.ADD)
        self._cat_add_btn.setObjectName("SaveButton")
        self._cat_add_btn.setFixedWidth(70)
        add_row.addWidget(self._cat_add_btn)

        layout.addLayout(add_row)

        self._cat_add_btn.clicked.connect(self._on_add_category)
        self._cat_name_input.returnPressed.connect(self._on_add_category)

        return w

    def _build_tag_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(8, 8, 8, 8)

        card, layout = self._build_card()
        self._tag_card_shadow = card.graphicsEffect()
        outer.addWidget(card)

        self._tag_search = SearchBar()
        self._tag_search.search_changed.connect(self._on_tag_search_changed)
        layout.addWidget(self._tag_search)

        self._tag_stack, self._tag_flow = build_flow_stack(
            AppStrings.EMPTY_TAGS_MSG,
            h_spacing=8, v_spacing=8,
            scroll_name="SettingsScrollArea",
        )
        layout.addWidget(self._tag_stack, stretch=1)
        layout.addWidget(self._card_separator())

        # Yeni etiket ekleme
        add_row = QHBoxLayout()
        add_row.setSpacing(6)

        self._tag_name_input = QLineEdit()
        self._tag_name_input.setObjectName("FormField")
        self._tag_name_input.setPlaceholderText(AppStrings.TAG_NAME)
        add_row.addWidget(self._tag_name_input, stretch=1)

        self._tag_add_btn = QPushButton(AppStrings.ADD)
        self._tag_add_btn.setObjectName("SaveButton")
        self._tag_add_btn.setFixedWidth(70)
        add_row.addWidget(self._tag_add_btn)

        layout.addLayout(add_row)

        self._tag_add_btn.clicked.connect(self._on_add_tag)
        self._tag_name_input.returnPressed.connect(self._on_add_tag)

        return w

    @staticmethod
    def _build_card() -> tuple[QFrame, QVBoxLayout]:
        """Liste + ekle-formunu tek gorsel kartta birlestiren yukseltilmis QFrame kurar."""
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

    @staticmethod
    def _card_separator() -> QFrame:
        line = QFrame()
        line.setObjectName("SettingsCardSeparator")
        line.setFixedHeight(1)
        return line

    # ------------------------------------------------------------------ #
    # Event Bus
    # ------------------------------------------------------------------ #

    def _connect_events(self) -> None:
        event_bus.category_added.connect(self._reload_categories)
        event_bus.category_updated.connect(self._reload_categories)
        event_bus.category_deleted.connect(self._reload_categories)
        event_bus.tag_added.connect(self._reload_tags)
        event_bus.tag_updated.connect(self._reload_tags)
        event_bus.tag_deleted.connect(self._reload_tags)
        event_bus.error_occurred.connect(self._banner.show_error)
        event_bus.theme_changed.connect(self._on_theme_changed)

    # ------------------------------------------------------------------ #
    # Veri yukleme
    # ------------------------------------------------------------------ #

    def load_all(self) -> None:
        self._reload_categories()
        self._reload_tags()

    def _on_theme_changed(self, theme_data: dict) -> None:
        shadow_color = to_qcolor(resolve_theme_color(theme_data, Colors.SHADOW))
        self._cat_card_shadow.setColor(shadow_color)
        self._tag_card_shadow.setColor(shadow_color)

    def _reload_categories(self, _id: int = 0) -> None:
        self._reload_rows(
            stack=self._cat_stack,
            flow=self._cat_flow,
            rows=self._category_rows,
            items=self._controller.load_categories(),
            row_cls=CategoryRow,
            on_edit=self._on_edit_category,
            on_delete=self._on_delete_category,
        )
        self._on_cat_search_changed(self._cat_search.text())

    def _reload_tags(self, _id: int = 0) -> None:
        self._reload_rows(
            stack=self._tag_stack,
            flow=self._tag_flow,
            rows=self._tag_rows,
            items=self._controller.load_tags(),
            row_cls=TagRow,
            on_edit=self._on_edit_tag,
            on_delete=self._on_delete_tag,
        )
        self._on_tag_search_changed(self._tag_search.text())

    def _on_cat_search_changed(self, text: str) -> None:
        self._filter_rows(self._cat_flow, self._category_rows, text)

    def _on_tag_search_changed(self, text: str) -> None:
        self._filter_rows(self._tag_flow, self._tag_rows, text)

    @staticmethod
    def _filter_rows(flow, rows: dict, text: str) -> None:
        needle = text.strip().lower()
        for row in rows.values():
            row.setVisible(not needle or needle in row.name.lower())
        flow.invalidate()

    @staticmethod
    def _reload_rows(*, stack, flow, rows: dict,
                     items: list, row_cls, on_edit, on_delete) -> None:
        clear_flow(flow)
        rows.clear()

        if not items:
            stack.setCurrentIndex(EMPTY_PAGE)
            return

        stack.setCurrentIndex(GRID_PAGE)
        for entry in items:
            row = row_cls(entry)
            row.edit_requested.connect(on_edit)
            row.delete_requested.connect(on_delete)
            flow.addWidget(row)
            rows[entry.id] = row

    # ------------------------------------------------------------------ #
    # Slot'lar
    # ------------------------------------------------------------------ #

    def _on_add_category(self) -> None:
        name = self._cat_name_input.text().strip()
        color = self._cat_color_picker.value()
        icon = self._cat_icon_input.text().strip()
        if not name:
            self._banner.show_error(AppStrings.ERR_CATEGORY_NAME_REQUIRED)
            return
        if not color:
            self._banner.show_error(AppStrings.ERR_COLOR_REQUIRED)
            return
        result = self._controller.create_category(name, color, icon)
        if result:
            self._cat_name_input.clear()
            self._cat_color_picker.clear()
            self._cat_icon_input.clear()
            self._banner.show_info(f"'{result.name}' kategorisi eklendi.")

    def _on_edit_category(self, cat_id: int, name: str,
                          color_hex: str, icon: str) -> None:
        self._controller.update_category(cat_id, name, color_hex, icon)

    def _on_delete_category(self, cat_id: int) -> None:
        self._controller.delete_category(cat_id)

    def _on_add_tag(self) -> None:
        name = self._tag_name_input.text().strip()
        if not name:
            self._banner.show_error("Etiket adi bos olamaz.")
            return
        result = self._controller.create_tag(name)
        if result:
            self._tag_name_input.clear()
            self._banner.show_info(f"'#{result.name}' etiketi eklendi.")

    def _on_edit_tag(self, tag_id: int, new_name: str) -> None:
        self._controller.update_tag(tag_id, new_name)

    def _on_delete_tag(self, tag_id: int) -> None:
        self._controller.delete_tag(tag_id)
