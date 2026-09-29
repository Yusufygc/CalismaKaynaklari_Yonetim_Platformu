from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlalchemy.orm import Session

from core.events import event_bus
from ui_qml.bridges.library_bridge import LibraryBridge
from ui_qml.bridges.market_bridge import MarketBridge
from ui_qml.bridges.reader_bridge import ReaderBridge
from ui_qml.bridges.settings_bridge import SettingsBridge
from ui_qml.context import BridgeContext, Controllers


class QmlBridge(QObject):
    """Python backend ile QML arasindaki kok kopru (composition root).

    Yalnizca uygulama kabugunu (tema, sade mod, aktif sayfa, tek toast kanali) tasir; is alanlari
    dort alt-bridge'e bolunmustur ve QML'e sabit property olarak sunulur:

    - `bridge.library`  -- kaynak listesi/filtre, detay cekmecesi, kaynak ekle-duzenle-sil, PDF iceri aktarma
    - `bridge.reader`   -- okuyucu, alinti/kelime/not, PDF anahati, atif ve OpenAlex bilgisi
    - `bridge.market`   -- Makale Market, kesif/oneri, kayitli aramalar
    - `bridge.settings` -- kategori ve etiket yonetimi

    Alt-bridge'ler birbirini dogrudan cagirmaz; kaynak/kategori/etiket degisiklikleri `core.events.event_bus`
    uzerinden akar. Bagimliliklar `BridgeContext` ile (DI) verilir.
    """

    isDarkThemeChanged = Signal(bool)
    currentViewChanged = Signal(str)
    isSimpleModeChanged = Signal(bool)
    notificationEmitted = Signal(str, str)  # type (info/error), message

    def __init__(
        self,
        session: Session | None = None,
        controllers: Controllers | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        if controllers is None:
            if session is None:
                raise ValueError("QmlBridge requires either a controllers container or a session.")
            controllers = Controllers.build(session)

        self._is_dark_theme = True
        self._is_simple_mode = False
        self._current_view = "showcase"

        self._ctx = BridgeContext(controllers)
        # Tek toast kanali: alt-bridge'ler `ctx.notify`'a yazar; controller hatalari (event_bus) da
        # buraya duser -- yoksa sadece log dosyasina gidip kullaniciya hic gorunmezdi.
        self._ctx.notify.emitted.connect(self.notificationEmitted)
        event_bus.error_occurred.connect(self._ctx.notify.error)

        self._settings = SettingsBridge(self._ctx, self)
        self._library = LibraryBridge(self._ctx, self)
        self._reader = ReaderBridge(self._ctx, self._library, self.setCurrentView, self)
        self._market = MarketBridge(self._ctx, self._library, self)

        self.refresh_all()  # Ilk veri yuklemesi

    # ------------------------------------------------------------------ #
    # Alt-bridge'ler (QML: bridge.library.* / reader / market / settings)
    # ------------------------------------------------------------------ #

    @Property(QObject, constant=True)
    def library(self) -> QObject:
        return self._library

    @Property(QObject, constant=True)
    def reader(self) -> QObject:
        return self._reader

    @Property(QObject, constant=True)
    def market(self) -> QObject:
        return self._market

    @Property(QObject, constant=True)
    def settings(self) -> QObject:
        return self._settings

    @property
    def controllers(self) -> Controllers:
        return self._ctx.controllers

    @property
    def ctx(self) -> BridgeContext:
        return self._ctx

    def refresh_all(self) -> None:
        for child in (self._library, self._settings, self._reader, self._market):
            child.refresh()

    # ------------------------------------------------------------------ #
    # Kabuk durumu
    # ------------------------------------------------------------------ #

    @Property(bool, notify=isDarkThemeChanged)
    def isDarkTheme(self) -> bool:
        return self._is_dark_theme

    @Property(str, notify=currentViewChanged)
    def currentView(self) -> str:
        return self._current_view

    @Property(bool, notify=isSimpleModeChanged)
    def isSimpleMode(self) -> bool:
        return self._is_simple_mode

    @Slot()
    def toggleTheme(self) -> None:
        self._is_dark_theme = not self._is_dark_theme
        self.isDarkThemeChanged.emit(self._is_dark_theme)

    @Slot(bool)
    def setSimpleMode(self, enabled: bool) -> None:
        if self._is_simple_mode != enabled:
            self._is_simple_mode = enabled
            self.isSimpleModeChanged.emit(self._is_simple_mode)

    @Slot(str)
    def setCurrentView(self, view_name: str) -> None:
        if self._current_view != view_name:
            self._current_view = view_name
            self.currentViewChanged.emit(self._current_view)
