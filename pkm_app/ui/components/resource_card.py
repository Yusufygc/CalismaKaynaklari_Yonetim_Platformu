from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import qtawesome as qta

from core.constants.colors import Colors
from core.constants.fonts import Fonts
from core.constants.icons import QtAwesomeIcons
from core.constants.status import status_label
from core.events import event_bus
from models import Resource, ResourceStatus
from ui.components.card_icon_button import FavoriteButton, PinButton
from ui.components.painted import AccentFrame, ColorBadge
from ui.text_utils import elide_to_lines
from ui.theme_utils import resolve_theme_color, valid_or_fallback, with_alpha
from utils.date_utils import format_date

_CARD_WIDTH = 240
_CARD_HEIGHT = 160

# QVBoxLayout setContentsMargins(12, 10, 12, 10) -> sol+sag 24px
_TEXT_AREA_WIDTH = _CARD_WIDTH - 24
_TITLE_MAX_LINES = 2
_DESC_MAX_LINES = 2


def _title_measure_font() -> QFont:
    """bkz. url_rich_card.py::_title_measure_font — cards.qss #CardTitle ile senkron."""
    font = QFont(Fonts.FAMILY_PRIMARY)
    font.setPixelSize(14)
    font.setBold(True)
    return font


def _desc_measure_font() -> QFont:
    """bkz. url_rich_card.py::_title_measure_font — cards.qss #CardDescription ile senkron."""
    font = QFont(Fonts.FAMILY_PRIMARY)
    font.setPixelSize(11)
    return font

_STATUS_COLOR_KEYS = {
    ResourceStatus.PLANNED: Colors.STATUS_PLANNED,
    ResourceStatus.IN_PROGRESS: Colors.STATUS_IN_PROGRESS,
    ResourceStatus.COMPLETED: Colors.STATUS_COMPLETED,
}


class ResourceCard(AccentFrame):
    """Standart metin/not kaynaklari icin sabit boyutlu kart."""

    def __init__(self, resource: Resource, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._resource = resource
        self._resource_id = resource.id
        self._theme_data: dict | None = None
        self._cat_icon_label: QLabel | None = None
        self._status_badge: ColorBadge | None = None
        self._description_label: QLabel | None = None
        self._tag_badges: list[ColorBadge] = []
        self._cat_icon_name = (
            resource.category.icon
            if resource.category and resource.category.icon
            else QtAwesomeIcons.CATEGORY
        )

        self.setObjectName("ResourceCard")
        self.setFixedSize(_CARD_WIDTH, _CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_accent_color(self._resolve_accent_color(resource))
        self.set_shadow_color(resolve_theme_color(self._theme_data, Colors.SHADOW))

        self._build_ui(resource)
        event_bus.theme_changed.connect(self._on_theme_changed)

    def _build_ui(self, resource: Resource) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        layout.addLayout(self._build_top_row(resource))
        layout.addWidget(self._build_title(resource))
        description_label = self._build_description(resource)
        if description_label is not None:
            layout.addWidget(description_label)
        layout.addStretch()
        layout.addLayout(self._build_bottom_row(resource))

    def _build_top_row(self, resource: Resource) -> QHBoxLayout:
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self._cat_icon_label = QLabel()
        self._cat_icon_label.setObjectName("CardCatIcon")
        self._update_category_icon()
        top_row.addWidget(self._cat_icon_label)
        top_row.addStretch()

        status_text = status_label(resource.status)
        if status_text:
            status_color = self._status_color(resource.status)
            self._status_badge = ColorBadge(
                status_text,
                status_color,
                with_alpha(status_color, "22"),
                vertical_padding=1,
            )
            top_row.addWidget(self._status_badge)

        self._pin_btn = PinButton(resource.id, bool(resource.is_pinned))
        self._favorite_btn = FavoriteButton(resource.id, bool(resource.is_favorite))
        top_row.addWidget(self._pin_btn)
        top_row.addWidget(self._favorite_btn)
        return top_row

    def _build_title(self, resource: Resource) -> QLabel:
        title_font = _title_measure_font()
        title = QLabel(elide_to_lines(resource.title, title_font, _TEXT_AREA_WIDTH, _TITLE_MAX_LINES))
        title.setObjectName("CardTitle")
        title.setWordWrap(True)
        title.setMaximumHeight(QFontMetrics(title_font).lineSpacing() * _TITLE_MAX_LINES)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return title

    def _build_description(self, resource: Resource) -> QLabel | None:
        description = self._description_text(resource)
        if not description:
            return None
        desc_font = _desc_measure_font()
        self._description_label = QLabel(
            elide_to_lines(description, desc_font, _TEXT_AREA_WIDTH, _DESC_MAX_LINES)
        )
        self._description_label.setObjectName("CardDescription")
        self._description_label.setWordWrap(True)
        self._description_label.setMaximumHeight(
            QFontMetrics(desc_font).lineSpacing() * _DESC_MAX_LINES
        )
        self._description_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        return self._description_label

    def _build_bottom_row(self, resource: Resource) -> QHBoxLayout:
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(4)

        date_label = QLabel(format_date(resource.created_at))
        date_label.setObjectName("CardDate")
        bottom_row.addWidget(date_label)
        bottom_row.addStretch()

        for tag in resource.tags[:3]:
            badge = ColorBadge(
                f"#{tag.name}",
                resolve_theme_color(self._theme_data, Colors.TEXT_SECONDARY),
                resolve_theme_color(self._theme_data, Colors.TAG_BADGE_BG),
                horizontal_padding=5,
                vertical_padding=1,
            )
            self._tag_badges.append(badge)
            bottom_row.addWidget(badge)

        return bottom_row

    def mousePressEvent(self, event) -> None:
        # Pin/favori butonlari kendi tiklamasini yutar; buraya gelinmez.
        # Diger alanlara tiklayinca kayit secimi yapilir.
        if self._pin_btn.underMouse() or self._favorite_btn.underMouse():
            return super().mousePressEvent(event)
        event_bus.resource_selected.emit(self._resource_id)
        super().mousePressEvent(event)

    def _on_theme_changed(self, theme_data: dict) -> None:
        self._theme_data = theme_data
        self.set_accent_color(self._resolve_accent_color(self._resource))
        self.set_shadow_color(resolve_theme_color(self._theme_data, Colors.SHADOW))
        if self._status_badge is not None:
            status_color = self._status_color(self._resource.status)
            self._status_badge.set_colors(status_color, with_alpha(status_color, "22"))
        for badge in self._tag_badges:
            badge.set_colors(
                resolve_theme_color(self._theme_data, Colors.TEXT_SECONDARY),
                resolve_theme_color(self._theme_data, Colors.TAG_BADGE_BG),
            )
        self._update_category_icon()
        self.update()

    def _status_color(self, status: ResourceStatus) -> str:
        key = _STATUS_COLOR_KEYS.get(status, Colors.ACCENT)
        return resolve_theme_color(self._theme_data, key)

    def _resolve_accent_color(self, resource: Resource) -> str:
        """Kart sol şerit rengi: kategori varsa kategori HEX, yoksa status fallback."""
        if resource.category and resource.category.color_hex:
            return valid_or_fallback(
                resource.category.color_hex,
                self._status_color(resource.status),
            )
        return self._status_color(resource.status)

    def _update_category_icon(self) -> None:
        if self._cat_icon_label is None:
            return
        icon_color = resolve_theme_color(self._theme_data, Colors.TEXT_SECONDARY)
        try:
            icon = qta.icon(self._cat_icon_name, color=icon_color)
        except Exception:
            icon = qta.icon(QtAwesomeIcons.CATEGORY, color=icon_color)
        self._cat_icon_label.setPixmap(icon.pixmap(16, 16))

    @staticmethod
    def _description_text(resource: Resource) -> str:
        content = (resource.content or "").strip()
        if content:
            return " ".join(content.split())
        if resource.extra_metadata:
            return " ".join(
                (resource.extra_metadata.get("og_description") or "").strip().split()
            )
        return ""
