from urllib.parse import urljoin

import requests

from PySide6.QtCore import QRunnable, QObject, Signal, Slot, QThreadPool, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QFontMetrics, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import qtawesome as qta

from core.constants.colors import Colors
from core.constants.fonts import Fonts
from core.constants.icons import QtAwesomeIcons
from core.constants.strings import AppStrings
from core.events import event_bus
from core.logger import log
from core.net_utils import is_blocked_host
from models import Resource
from ui.components.card_icon_button import FavoriteButton, PinButton
from ui.components.painted import AccentFrame, ColorBadge
from ui.text_utils import elide_to_lines
from ui.theme_utils import resolve_theme_color, valid_or_fallback, with_alpha

_CARD_WIDTH = 320
_CARD_HEIGHT = 380
_THUMB_HEIGHT = 180

# text_area setContentsMargins(14, 10, 14, 6) -> sol+sag 28px
_TEXT_AREA_WIDTH = _CARD_WIDTH - 28
_TITLE_MAX_LINES = 2
_DESC_MAX_LINES = 3


def _title_measure_font() -> QFont:
    """Yalnizca satir kirpme HESABI icin; gercek render fontu cards.qss
    (#UrlCardTitle) uzerinden gelir. QSS'teki piksel/weight degisirse burasi da
    guncellenmeli. QApplication olusmadan QFont guvenilir olmadigi icin
    modul importunda degil, ilk kullanimda (instance construction) cagrilir.
    """
    font = QFont(Fonts.FAMILY_PRIMARY)
    font.setPixelSize(15)
    font.setBold(True)
    return font


def _desc_measure_font() -> QFont:
    """bkz. _title_measure_font — cards.qss #UrlCardDesc ile senkron tutulmali."""
    font = QFont(Fonts.FAMILY_PRIMARY)
    font.setPixelSize(12)
    return font

_THUMBNAIL_CACHE: dict[str, QPixmap] = {}


class WorkerSignals(QObject):
    """Asenkron işçiden ana thread'e veri ileten sinyaller."""
    finished = Signal(str, bytes)  # url, downloaded_bytes
    error = Signal(str, str)       # url, error_msg


class ThumbnailWorker(QRunnable):
    """Arka planda görsel indirip ana thread'e ileten işçi.

    Gorsel URL'si kaynagi taranan (dolayisiyla saldirgan etkisindeki) sayfanin
    og:image/twitter:image meta etiketinden geliyor -- ScraperService._safe_get
    ile ayni SSRF/redirect disiplinine tabi olmali (bkz. core/net_utils.py).
    """

    _TIMEOUT_SECONDS = 8
    _MAX_REDIRECTS = 5
    _HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.signals = WorkerSignals()
        self._is_aborted = False

    def abort(self) -> None:
        self._is_aborted = True

    def run(self) -> None:
        if self._is_aborted:
            return
        try:
            response = self._safe_get(self.url)
            if response is None:
                raise ValueError("URL reddedildi (ic ag/loopback veya yonlendirme siniri)")
            if self._is_aborted:
                return
            self.signals.finished.emit(self.url, response.content)
        except Exception as e:
            if not self._is_aborted:
                self.signals.error.emit(self.url, str(e))

    def _safe_get(self, url: str) -> requests.Response | None:
        current_url = url
        for _ in range(self._MAX_REDIRECTS + 1):
            if is_blocked_host(current_url):
                return None
            response = requests.get(
                current_url,
                headers=self._HEADERS,
                timeout=self._TIMEOUT_SECONDS,
                allow_redirects=False,
            )
            if response.is_redirect:
                location = response.headers.get("Location")
                if not location:
                    return None
                current_url = urljoin(current_url, location)
                continue
            response.raise_for_status()
            return response
        return None


class UrlRichCard(AccentFrame):
    """URL kaynaklari icin buyuk, gorsel odakli kart (URL Vitrini)."""

    def __init__(self, resource: Resource, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._resource = resource
        self._resource_id = resource.id
        self._url = resource.url or ""
        self._theme_data: dict | None = None
        self._worker: ThumbnailWorker | None = None
        self._open_btn: QPushButton | None = None
        self._thumb_label: QLabel | None = None
        self._desc_label: QLabel | None = None
        self._pin_btn: PinButton | None = None
        self._favorite_btn: FavoriteButton | None = None
        self._thumbnail_url: str | None = None
        self._thumbnail_loaded = False

        self.setObjectName("UrlRichCard")
        self.setFixedSize(_CARD_WIDTH, _CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_accent_color(self._resolve_border_color(resource))
        self.set_shadow_color(resolve_theme_color(self._theme_data, Colors.SHADOW))

        self._build_ui(resource)
        self.destroyed.connect(self._cleanup_network)
        event_bus.theme_changed.connect(self._on_theme_changed)

    def _resolve_border_color(self, resource: Resource) -> str:
        if resource.category and resource.category.color_hex:
            return valid_or_fallback(
                resource.category.color_hex,
                resolve_theme_color(self._theme_data, Colors.CATEGORY_FALLBACK),
            )
        if resource.tags:
            return resolve_theme_color(self._theme_data, Colors.ACCENT)
        return resolve_theme_color(self._theme_data, Colors.BORDER)

    def _build_ui(self, resource: Resource) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(0)

        self._thumb_label = QLabel()
        self._thumb_label.setObjectName("CardThumbnail")
        self._thumb_label.setFixedHeight(_THUMB_HEIGHT)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._thumbnail_url = (
            resource.extra_metadata.get("thumbnail") if resource.extra_metadata else None
        )
        if self._thumbnail_url:
            self._load_thumbnail(self._thumbnail_url)
        else:
            self._set_thumbnail_placeholder()

        layout.addWidget(self._thumb_label)

        text_area = QVBoxLayout()
        text_area.setContentsMargins(14, 10, 14, 6)
        text_area.setSpacing(6)

        meta_title: str = (
            resource.extra_metadata.get("og_title", resource.title)
            if resource.extra_metadata else resource.title
        )
        title_font = _title_measure_font()
        title_label = QLabel(
            elide_to_lines(meta_title, title_font, _TEXT_AREA_WIDTH, _TITLE_MAX_LINES)
        )
        title_label.setObjectName("UrlCardTitle")
        title_label.setWordWrap(True)
        title_label.setMaximumHeight(QFontMetrics(title_font).lineSpacing() * _TITLE_MAX_LINES)
        text_area.addWidget(title_label)

        meta_desc: str = (
            resource.extra_metadata.get("og_description", "")
            if resource.extra_metadata else ""
        ) or (resource.content or "")
        if meta_desc:
            desc_font = _desc_measure_font()
            self._desc_label = QLabel(
                elide_to_lines(meta_desc, desc_font, _TEXT_AREA_WIDTH, _DESC_MAX_LINES)
            )
            self._desc_label.setObjectName("UrlCardDesc")
            self._desc_label.setWordWrap(True)
            self._desc_label.setMaximumHeight(QFontMetrics(desc_font).lineSpacing() * _DESC_MAX_LINES)
            text_area.addWidget(self._desc_label)

        layout.addLayout(text_area)
        layout.addStretch()

        bottom = QHBoxLayout()
        bottom.setContentsMargins(14, 0, 14, 0)
        bottom.setSpacing(8)

        if resource.category:
            category_color = valid_or_fallback(
                resource.category.color_hex,
                resolve_theme_color(self._theme_data, Colors.CATEGORY_FALLBACK),
            )
            bottom.addWidget(
                ColorBadge(
                    resource.category.name,
                    category_color,
                    with_alpha(category_color, "22"),
                )
            )

        bottom.addStretch()

        self._pin_btn = PinButton(resource.id, bool(resource.is_pinned))
        self._favorite_btn = FavoriteButton(resource.id, bool(resource.is_favorite))
        bottom.addWidget(self._pin_btn)
        bottom.addWidget(self._favorite_btn)

        self._open_btn = QPushButton(AppStrings.OPEN_IN_BROWSER)
        self._open_btn.setObjectName("UrlOpenButton")
        self._open_btn.clicked.connect(self._open_in_browser)
        self._update_open_icon()
        bottom.addWidget(self._open_btn)

        layout.addLayout(bottom)

    def mousePressEvent(self, event) -> None:
        consumed_by_button = (
            (self._open_btn is not None and self._open_btn.underMouse())
            or (self._pin_btn is not None and self._pin_btn.underMouse())
            or (self._favorite_btn is not None and self._favorite_btn.underMouse())
        )
        if not consumed_by_button:
            event_bus.resource_selected.emit(self._resource_id)
        super().mousePressEvent(event)

    def _open_in_browser(self) -> None:
        if self._url:
            QDesktopServices.openUrl(QUrl(self._url))

    def _on_theme_changed(self, theme_data: dict) -> None:
        self._theme_data = theme_data
        self.set_accent_color(self._resolve_border_color(self._resource))
        self.set_shadow_color(resolve_theme_color(self._theme_data, Colors.SHADOW))
        self._update_open_icon()
        if not self._thumbnail_loaded:
            self._set_thumbnail_placeholder()
        self.update()

    def _update_open_icon(self) -> None:
        if self._open_btn is None:
            return
        color = resolve_theme_color(self._theme_data, Colors.ACCENT)
        self._open_btn.setIcon(qta.icon(QtAwesomeIcons.OPEN_BROWSER, color=color))

    def _set_thumbnail_placeholder(self) -> None:
        if self._thumb_label is None:
            return
        color = resolve_theme_color(self._theme_data, Colors.BORDER)
        placeholder = qta.icon(QtAwesomeIcons.URL_SHOWCASE, color=color).pixmap(48, 48)
        self._thumb_label.setPixmap(placeholder)

    def _load_thumbnail(self, thumbnail_url: str) -> None:
        self._set_thumbnail_placeholder()
        if not thumbnail_url:
            return

        # 1. Bellek Önbelleği (Cache) Kontrolü
        if thumbnail_url in _THUMBNAIL_CACHE:
            log.info("Gorsel bellekten yukleniyor: %s", thumbnail_url)
            self._thumb_label.setPixmap(_THUMBNAIL_CACHE[thumbnail_url])
            self._thumbnail_loaded = True
            return

        # 2. Önceki aktif isteği iptal et
        self._cleanup_network()

        # 3. Arka plan thread ile istek başlat
        log.info("Gorsel indiriliyor (yeni istek): %s", thumbnail_url)
        self._worker = ThumbnailWorker(thumbnail_url)
        self._worker.signals.finished.connect(self._on_thumbnail_finished)
        self._worker.signals.error.connect(self._on_thumbnail_error)
        QThreadPool.globalInstance().start(self._worker)

    @Slot(str, bytes)
    def _on_thumbnail_finished(self, url: str, data: bytes) -> None:
        if url != self._thumbnail_url:
            return
        self._worker = None

        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            log.warning("Kucuk resim decode edilemedi: %s", url)
            return

        scaled = pixmap.scaled(
            _CARD_WIDTH,
            _THUMB_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

        _THUMBNAIL_CACHE[url] = scaled
        if self._thumb_label is not None:
            self._thumb_label.setPixmap(scaled)
            self._thumbnail_loaded = True
            log.info("Gorsel basariyla yuklendi ve olceklendi: %s", url)

    @Slot(str, str)
    def _on_thumbnail_error(self, url: str, error_msg: str) -> None:
        if url != self._thumbnail_url:
            return
        self._worker = None
        log.warning("Kucuk resim indirilemedi: %s - Hata: %s", url, error_msg)

    def _cleanup_network(self) -> None:
        if self._worker:
            log.info("_cleanup_network: aktif isci iptal ediliyor")
            self._worker.abort()
            self._worker = None
