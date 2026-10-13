from PySide6.QtCore import Property, QObject, Signal, Slot

from core.constants.appearance import (
    DEFAULT_FONT_PAIR,
    DEFAULT_PALETTE,
    FONT_PAIR_IDS,
    PALETTE_IDS,
    SETTING_FONT_PAIR,
    SETTING_PALETTE,
)
from ui_qml.context import BridgeContext


class AppearanceBridge(QObject):
    """Ayarlar > Gorunum: renk temasi ve yazi tipi cifti secimi. Secimler kullanici ayarlarinda saklanir; renkleri ve
    yazi tiplerini turetmek QML'dedir (`qml/theme/palettes.js`, `fonts.js`), burasi yalniz kimligi tutar/dogrular.
    Acik/koyu mod `QmlBridge.isDarkTheme`/`toggleTheme`tedir."""

    paletteChanged = Signal()
    fontPairChanged = Signal()

    def __init__(self, ctx: BridgeContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._palette = self._stored(SETTING_PALETTE, PALETTE_IDS, DEFAULT_PALETTE)
        self._font_pair = self._stored(SETTING_FONT_PAIR, FONT_PAIR_IDS, DEFAULT_FONT_PAIR)

    def _stored(self, key: str, allowed: tuple[str, ...], default: str) -> str:
        value = self._ctx.user_settings.get(key, default)
        return value if value in allowed else default  # bozuk/eski deger varsayilana duser

    @Property(str, notify=paletteChanged)
    def paletteId(self) -> str:
        return self._palette

    @Property(str, notify=fontPairChanged)
    def fontPairId(self) -> str:
        return self._font_pair

    @Slot(str)
    def setPalette(self, palette_id: str) -> None:
        if palette_id not in PALETTE_IDS or palette_id == self._palette:
            return
        if not self._ctx.user_settings.set(SETTING_PALETTE, palette_id):
            self._ctx.notify.error("Ayar kaydedilemedi.")
            return
        self._palette = palette_id
        self.paletteChanged.emit()

    @Slot(str)
    def setFontPair(self, pair_id: str) -> None:
        if pair_id not in FONT_PAIR_IDS or pair_id == self._font_pair:
            return
        if not self._ctx.user_settings.set(SETTING_FONT_PAIR, pair_id):
            self._ctx.notify.error("Ayar kaydedilemedi.")
            return
        self._font_pair = pair_id
        self.fontPairChanged.emit()

    @Slot()
    def reset(self) -> None:
        """Tema ve yazi tipi ciftini varsayilana dondurur."""
        self.setPalette(DEFAULT_PALETTE)
        self.setFontPair(DEFAULT_FONT_PAIR)
