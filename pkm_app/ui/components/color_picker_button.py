from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from core.constants.colors import Colors
from core.constants.strings import AppStrings
from core.events import event_bus
from ui.components.painted import ColorSwatch
from ui.theme_utils import resolve_theme_color


class ColorPickerButton(QPushButton):
    """Kategori rengi icin QColorDialog tabanli secici buton.

    Buton ici: sol kose ColorSwatch + sag taraf hex metni veya placeholder.
    Tiklandiginda QColorDialog acar; sonuc gecerliyse `color_changed(#RRGGBB)`
    sinyali fırlatir.
    """

    color_changed = Signal(str)

    def __init__(self, initial_color: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ColorPickerButton")
        self.setCursor(self.cursor())
        self._color: str = ""
        self._theme_data: dict | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 10, 4)
        layout.setSpacing(8)

        self._swatch = ColorSwatch(
            initial_color,
            resolve_theme_color(self._theme_data, Colors.CATEGORY_FALLBACK),
            resolve_theme_color(self._theme_data, Colors.SWATCH_BORDER),
        )
        layout.addWidget(self._swatch)

        self._text = QLabel()
        self._text.setObjectName("ColorPickerText")
        layout.addWidget(self._text, stretch=1)

        self.set_value(initial_color)
        self.clicked.connect(self._open_dialog)
        event_bus.theme_changed.connect(self._on_theme_changed)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def value(self) -> str:
        return self._color

    def set_value(self, color_hex: str) -> None:
        color_hex = (color_hex or "").strip()
        if color_hex and not QColor(color_hex).isValid():
            color_hex = ""
        self._color = color_hex
        self._text.setText(color_hex or AppStrings.PICK_COLOR_PLACEHOLDER)
        self._refresh_swatch()

    def clear(self) -> None:
        self.set_value("")

    # ------------------------------------------------------------------ #
    # Slot'lar
    # ------------------------------------------------------------------ #

    def _open_dialog(self) -> None:
        default_color = resolve_theme_color(self._theme_data, Colors.ACCENT)
        initial = QColor(self._color) if self._color else QColor(default_color)
        chosen = QColorDialog.getColor(
            initial,
            self,
            AppStrings.PICK_COLOR_TITLE,
        )
        if not chosen.isValid():
            return
        hex_value = chosen.name().upper()
        self.set_value(hex_value)
        self.color_changed.emit(hex_value)

    def _on_theme_changed(self, theme_data: dict) -> None:
        self._theme_data = theme_data
        self._refresh_swatch()

    def _refresh_swatch(self) -> None:
        self._swatch.set_color(
            self._color,
            resolve_theme_color(self._theme_data, Colors.CATEGORY_FALLBACK),
            resolve_theme_color(self._theme_data, Colors.SWATCH_BORDER),
        )
