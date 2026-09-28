from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QToolButton,
    QWidget,
    QWidgetAction,
)

import qtawesome as qta

from core.constants.colors import Colors
from core.constants.icons import QtAwesomeIcons
from core.constants.status import status_label
from core.constants.strings import AppStrings
from core.events import event_bus
from models import ResourceStatus
from ui.components.flow_layout import FlowLayout
from ui.theme_utils import resolve_theme_color, to_qcolor


_PRIORITY_LABELS = [
    (1, AppStrings.FORM_PRIORITY_HIGH),
    (2, AppStrings.FORM_PRIORITY_MEDIUM),
    (3, AppStrings.FORM_PRIORITY_LOW),
]


class _ToggleChip(QPushButton):
    """Tek satirlik secilebilir chip."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("FilterChip")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)


class FilterBar(QFrame):
    """Kategori + Etiket + Durum + Oncelik kombinasyonel filtre cubugu.

    Herhangi bir kontrol degisince `filters_changed(dict)` emit eder.
    Sozluk semasi:
      {
        "category_id": int|None,
        "tag_ids": list[int],
        "statuses": list[ResourceStatus],
        "priorities": list[int],
      }
    """

    filters_changed = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FilterBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._categories: list = []
        self._tags: list = []
        self._status_chips: dict[ResourceStatus, _ToggleChip] = {}
        self._priority_chips: dict[int, _ToggleChip] = {}
        self._suppress_emit = False

        self._shadow_effect = QGraphicsDropShadowEffect(self)
        self._shadow_effect.setBlurRadius(20)
        self._shadow_effect.setOffset(0, 3)
        self._shadow_effect.setColor(to_qcolor(resolve_theme_color(None, Colors.SHADOW)))
        self.setGraphicsEffect(self._shadow_effect)

        self._build_ui()
        self._update_clear_button_state()
        event_bus.theme_changed.connect(self._on_theme_changed)

    # ------------------------------------------------------------------ #
    # Kurulum
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        layout = FlowLayout(self, h_spacing=8, v_spacing=6)
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)

        self._build_category_filter(layout)
        layout.addWidget(self._separator())
        self._build_tag_filter(layout)
        layout.addWidget(self._separator())
        self._build_status_chips(layout)
        layout.addWidget(self._separator())
        self._build_priority_chips(layout)
        layout.addWidget(self._separator())
        self._build_favorite_chip(layout)
        self._build_clear_button(layout)

    def _build_category_filter(self, layout: FlowLayout) -> None:
        layout.addWidget(self._label(AppStrings.FILTER_CATEGORY))
        self._category_combo = QComboBox()
        self._category_combo.setObjectName("FilterCombo")
        self._category_combo.addItem(AppStrings.FILTER_ANY, None)
        self._category_combo.currentIndexChanged.connect(self._emit_filters)
        layout.addWidget(self._category_combo)

    def _build_tag_filter(self, layout: FlowLayout) -> None:
        layout.addWidget(self._label(AppStrings.FILTER_TAG))
        self._tag_button = QToolButton()
        self._tag_button.setObjectName("FilterTagButton")
        self._tag_button.setText(AppStrings.FILTER_TAG_PLACEHOLDER)
        self._tag_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._tag_menu = QMenu(self._tag_button)
        self._tag_list = QListWidget()
        self._tag_list.setObjectName("FilterTagList")
        self._tag_list.setMinimumWidth(180)
        self._tag_list.setMaximumHeight(220)
        self._tag_list.itemChanged.connect(self._on_tag_item_changed)
        tag_action = QWidgetAction(self._tag_menu)
        tag_action.setDefaultWidget(self._tag_list)
        self._tag_menu.addAction(tag_action)
        self._tag_button.setMenu(self._tag_menu)
        layout.addWidget(self._tag_button)

    def _build_status_chips(self, layout: FlowLayout) -> None:
        layout.addWidget(self._label(AppStrings.FILTER_STATUS))
        for status in ResourceStatus:
            chip = _ToggleChip(status_label(status))
            chip.toggled.connect(self._emit_filters)
            self._status_chips[status] = chip
            layout.addWidget(chip)

    def _build_priority_chips(self, layout: FlowLayout) -> None:
        layout.addWidget(self._label(AppStrings.FILTER_PRIORITY))
        for value, label in _PRIORITY_LABELS:
            chip = _ToggleChip(label)
            chip.toggled.connect(self._emit_filters)
            self._priority_chips[value] = chip
            layout.addWidget(chip)

    def _build_favorite_chip(self, layout: FlowLayout) -> None:
        self._favorite_chip = _ToggleChip(AppStrings.FAVORITES)
        self._favorite_chip.toggled.connect(self._emit_filters)
        layout.addWidget(self._favorite_chip)

    def _build_clear_button(self, layout: FlowLayout) -> None:
        self._clear_btn = QToolButton()
        self._clear_btn.setObjectName("FilterClearButton")
        self._clear_btn.setText(AppStrings.FILTER_CLEAR)
        self._clear_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._refresh_clear_icon()
        self._clear_btn.clicked.connect(self.clear)
        layout.addWidget(self._clear_btn)

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FilterLabel")
        return lbl

    @staticmethod
    def _separator() -> QFrame:
        line = QFrame()
        line.setObjectName("FilterSeparator")
        line.setFixedWidth(1)
        return line

    def _refresh_clear_icon(self) -> None:
        color = resolve_theme_color(None, Colors.ICON)
        self._clear_btn.setIcon(qta.icon(QtAwesomeIcons.FILTER_CLEAR, color=color))

    def _on_theme_changed(self, theme_data: dict) -> None:
        color = resolve_theme_color(theme_data, Colors.ICON)
        self._clear_btn.setIcon(qta.icon(QtAwesomeIcons.FILTER_CLEAR, color=color))
        self._shadow_effect.setColor(to_qcolor(resolve_theme_color(theme_data, Colors.SHADOW)))

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def set_categories(self, categories: list) -> None:
        self._categories = list(categories)
        self._suppress_emit = True
        current = self._category_combo.currentData()
        self._category_combo.clear()
        self._category_combo.addItem(AppStrings.FILTER_ANY, None)
        for cat in self._categories:
            self._category_combo.addItem(cat.name, cat.id)
        idx = self._category_combo.findData(current)
        self._category_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._suppress_emit = False
        self._update_clear_button_state()

    def set_tags(self, tags: list) -> None:
        self._tags = list(tags)
        current_ids = set(self._selected_tag_ids())
        self._suppress_emit = True
        self._tag_list.clear()
        for tag in self._tags:
            item = QListWidgetItem(f"#{tag.name}")
            item.setData(Qt.ItemDataRole.UserRole, tag.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if tag.id in current_ids else Qt.CheckState.Unchecked
            )
            self._tag_list.addItem(item)
        self._suppress_emit = False
        self._refresh_tag_button_text()
        self._update_clear_button_state()

    def current_filters(self) -> dict:
        return {
            "category_id": self._category_combo.currentData(),
            "tag_ids": self._selected_tag_ids(),
            "statuses": [s for s, chip in self._status_chips.items() if chip.isChecked()],
            "priorities": [p for p, chip in self._priority_chips.items() if chip.isChecked()],
            "favorites_only": getattr(self, "_favorite_chip", None) is not None and self._favorite_chip.isChecked(),
        }

    def clear(self, notify: bool = True) -> None:
        self._suppress_emit = True
        self._category_combo.setCurrentIndex(0)
        for i in range(self._tag_list.count()):
            self._tag_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        for chip in self._status_chips.values():
            chip.setChecked(False)
        for chip in self._priority_chips.values():
            chip.setChecked(False)
        if getattr(self, "_favorite_chip", None):
            self._favorite_chip.setChecked(False)
        self._suppress_emit = False
        self._refresh_tag_button_text()
        self._update_clear_button_state()
        if notify:
            self._emit_filters()

    # ------------------------------------------------------------------ #
    # Slot'lar
    # ------------------------------------------------------------------ #

    def _selected_tag_ids(self) -> list[int]:
        return [
            self._tag_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._tag_list.count())
            if self._tag_list.item(i).checkState() == Qt.CheckState.Checked
        ]

    def _on_tag_item_changed(self, _item: QListWidgetItem) -> None:
        self._refresh_tag_button_text()
        self._emit_filters()

    def _refresh_tag_button_text(self) -> None:
        ids = self._selected_tag_ids()
        if not ids:
            self._tag_button.setText(AppStrings.FILTER_TAG_PLACEHOLDER)
        else:
            self._tag_button.setText(f"{AppStrings.FILTER_TAG} ({len(ids)})")

    def _emit_filters(self, *_args) -> None:
        if self._suppress_emit:
            return
        self._update_clear_button_state()
        self.filters_changed.emit(self.current_filters())

    def _update_clear_button_state(self) -> None:
        filters = self.current_filters()
        has_active = bool(
            filters.get("category_id")
            or filters.get("tag_ids")
            or filters.get("statuses")
            or filters.get("priorities")
            or filters.get("favorites_only")
        )
        self._clear_btn.setEnabled(has_active)
