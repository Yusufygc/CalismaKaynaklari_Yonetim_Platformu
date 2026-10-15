from PySide6.QtCore import Property, QObject, Signal, Slot, QTimer
from sqlalchemy.orm import Session

from core.constants.appearance import SETTING_DARK
from core.events import event_bus
from pdfkit.api import PdfBridge
from ui_qml.bridges.annotations_bridge import AnnotationsBridge
from ui_qml.bridges.appearance_bridge import AppearanceBridge
from ui_qml.bridges.citations_bridge import CitationsBridge
from ui_qml.bridges.discovery_bridge import DiscoveryBridge
from ui_qml.bridges.library_bridge import LibraryBridge
from ui_qml.bridges.market_bridge import MarketBridge
from ui_qml.bridges.reader_bridge import ReaderBridge
from ui_qml.bridges.searches_bridge import SearchesBridge
from ui_qml.bridges.settings_bridge import SettingsBridge
from ui_qml.bridges.metadata_bridge import MetadataBridge
from ui_qml.bridges.search_bridge import SearchBridge
from ui_qml.bridges.synthesis_bridge import SynthesisBridge
from ui_qml.bridges.update_bridge import UpdateBridge
from ui_qml.bridges.vault_bridge import VaultBridge
from ui_qml.context import BridgeContext, Controllers
from ui_qml.deep_links import DeepLinkRouter
from ui_qml.saved_search_state import SavedSearchState


class QmlBridge(QObject):
    """Python backend ile QML arasindaki kok kopru (composition root).

    Yalnizca uygulama kabugunu (tema, sade mod, aktif sayfa, tek toast kanali) tasir; is alanlari
    dort alt-bridge'e bolunmustur ve QML'e sabit property olarak sunulur:

    - `bridge.library`  -- kaynak listesi/filtre, detay cekmecesi, kaynak ekle-duzenle-sil, PDF iceri aktarma
    - `bridge.reader`   -- okuyucuyu ac/kapat, PDF indirme/anahat, Markdown disa aktarim
    - `bridge.annotations` -- alinti, kelime havuzu, PDF sayfa notlari
    - `bridge.pdf`      -- pdfkit: PDF belgesi, alinti modelleri (artimli), sayfa filtreleri (bkz. docs/plans/pdfkit-faz3-plani.md)
    - `bridge.vault`    -- Obsidian vault klasoru, esitleme durumu (pdfkit.VaultSync)
    - `bridge.contentSearch` -- PDF icerigi tam metin aramasi (pdfkit.SearchService / TextIndexer)
    - `bridge.synthesis` -- Bilgi Havuzu > Matris: literatur matrisi (kaynak x anlam etiketi), suzgecler, Markdown disa aktarim
    - `bridge.appearance` -- Ayarlar > Gorunum: renk temasi ve yazi tipi cifti (acik/koyu mod `isDarkTheme`/`toggleTheme`)
    - `bridge.metadata` -- Ayarlar > Kunye: yeni PDF'in kunyesini OpenAlex'ten otomatik doldurma (acik/kapali)
    - `bridge.citations` -- atif metni, OpenAlex bilgisi, referans/atif listeleri
    - `bridge.market`   -- Makale Market aramasi, sayfalama, gecmis, kaydetme/disa aktarma
    - `bridge.discovery` -- Market kart kesfi (referans/atif/benzer/yazar) ve kutuphaneden oneriler
    - `bridge.searches` -- kayitli aramalar ve yeni yayin takibi
    - `bridge.settings` -- kategori ve etiket yonetimi

    Alt-bridge'ler birbirini dogrudan cagirmaz; kaynak/kategori/etiket degisiklikleri `core.events.event_bus`
    uzerinden akar. Bagimliliklar `BridgeContext` ile (DI) verilir.
    """

    isDarkThemeChanged = Signal(bool)
    currentViewChanged = Signal(str)
    isSimpleModeChanged = Signal(bool)
    notificationEmitted = Signal(str, str)  # type (info/error), message
    windowActivationRequested = Signal()  # derin baglanti / ikinci ornek: pencere one getirilsin

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
        search_state = SavedSearchState(self)
        self._annotations = AnnotationsBridge(self._ctx, self._reader, self)
        self._pdf = PdfBridge(self._ctx.pdf_library, self)
        self._pdf.notification.connect(self._on_pdf_notification)
        self._pdf.contentChanged.connect(self._on_pdf_content_changed)
        self._pdf.readingProgressChanged.connect(lambda _resource_id: self._library.refresh_progress())
        self._vault = VaultBridge(self._ctx, self)
        self._content_search = SearchBridge(self._ctx, self._reader, self._pdf, self)
        self._metadata = MetadataBridge(self._ctx, self)
        self._appearance = AppearanceBridge(self._ctx, self)
        self._is_dark_theme = self._ctx.user_settings.get(SETTING_DARK, True) is not False  # son secilen mod
        self._synthesis = SynthesisBridge(self._ctx, self._reader, self._pdf, self)
        self.deep_links = DeepLinkRouter(self, self._ctx, self)
        self.deep_links.activationRequested.connect(self.windowActivationRequested)
        # Alinti/not/kelime ya da kaynak kunyesi (baslik, durum) degisince vault notu yeniden uretilir (1,5 sn birlesik).
        self._pdf.contentChanged.connect(self._ctx.vault_sync.mark_resource)
        event_bus.resource_updated.connect(self._ctx.vault_sync.mark_resource)
        self._citations = CitationsBridge(self._ctx, self._library, self._reader, self)
        self._market = MarketBridge(self._ctx, self._library, search_state, self)
        self._discovery = DiscoveryBridge(self._ctx, self._library, self)
        self._searches = SearchesBridge(self._ctx, self._market, search_state, self)
        self._update = UpdateBridge(self._ctx, self)

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
    def annotations(self) -> QObject:
        return self._annotations

    @Property(QObject, constant=True)
    def pdf(self) -> QObject:
        return self._pdf

    @Property(QObject, constant=True)
    def vault(self) -> QObject:
        return self._vault

    @Property(QObject, constant=True)
    def contentSearch(self) -> QObject:
        return self._content_search

    @Property(QObject, constant=True)
    def metadata(self) -> QObject:
        return self._metadata

    @Property(QObject, constant=True)
    def appearance(self) -> QObject:
        return self._appearance

    @Property(QObject, constant=True)
    def synthesis(self) -> QObject:
        return self._synthesis

    @Property(QObject, constant=True)
    def citations(self) -> QObject:
        return self._citations

    @Property(QObject, constant=True)
    def market(self) -> QObject:
        return self._market

    @Property(QObject, constant=True)
    def discovery(self) -> QObject:
        return self._discovery

    @Property(QObject, constant=True)
    def searches(self) -> QObject:
        return self._searches

    @Property(QObject, constant=True)
    def settings(self) -> QObject:
        return self._settings

    @Property(QObject, constant=True)
    def update(self) -> QObject:
        return self._update

    def _on_pdf_content_changed(self, resource_id: int) -> None:
        """PDF'te alinti/not/kelime degisti: havuz birlestirilerek tazelenir, acik cekmece guncellenir."""
        self._annotations.schedule_refresh()
        if self._library.isDrawerOpen:  # Kapaliysa cekmece sonraki acilista (selectResource) zaten yeniden kurulur.
            self._library.update_selected_if_matches(resource_id)

    def _on_pdf_notification(self, kind: str, message: str) -> None:
        (self._ctx.notify.error if kind == "error" else self._ctx.notify.info)(message)

    @property
    def controllers(self) -> Controllers:
        return self._ctx.controllers

    @property
    def ctx(self) -> BridgeContext:
        return self._ctx

    def refresh_all(self) -> None:
        self._library.reload()
        for child in (self._settings, self._annotations, self._searches):
            child.refresh()

    # ------------------------------------------------------------------ #
    # Kabuk durumu
    # ------------------------------------------------------------------ #

    def run_startup_tasks(self) -> None:
        """Pencere acildiktan sonra bir kez: PDF deposu bakimi ve sessiz guncelleme denetimi."""
        self._vault.restore()
        self._ctx.pdf_library.start_maintenance()
        # Pencere çizildikten 3 sn sonra sessiz güncelleme denetimi (testlerde ağa çıkmaz)
        QTimer.singleShot(3000, self._update.startupCheck)

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
        self._ctx.user_settings.set(SETTING_DARK, self._is_dark_theme)  # hatada mod yine degisir, yalniz hatirlanmaz
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
