import re
import uuid
from datetime import timedelta
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QObject,
    QPointF,
    QThreadPool,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtPdf import QPdfDocument

from core.constants.highlight_labels import HIGHLIGHT_LABELS, label_for_color
from core.constants.strings import AppStrings
from core.events import event_bus
from core.logger import log
from core.paths import pdf_storage_dir
from models import Resource, ResourceStatus
from controllers.main_controller import MainController
from services.paper_market_service import (
    MARKET_SORTS,
    MarketFilters,
    MarketPage,
    PaperMarketService,
    PaperResult,
)
from workers import (
    ExtractWorker as _ExtractWorker,
    MarketSearchWorker as _MarketSearchWorker,
    PaperMetadataWorker as _PaperMetadataWorker,
    PdfDownloadWorker as _PdfDownloadWorker,
    PdfImportWorker as _PdfImportWorker,
    PdfOutlineWorker as _PdfOutlineWorker,
    ReadingSuggestionWorker as _ReadingSuggestionWorker,
    SavedSearchCheckWorker as _SavedSearchCheckWorker,
    RelatedPapersWorker as _RelatedPapersWorker,
    ScrapeWorker as _ScrapeWorker,
)
from services.citation_service import CitationService
from services.export_service import ExportService
from services.library_index import LibraryIndex
from services.paper_export_service import PaperExportService
from services.pdf_download_service import looks_like_remote_pdf
from ui_qml.models.resource_list_model import ResourceListModel
from utils.text_utils import extract_sentence, sanitize_utf8
from utils.date_utils import format_local_datetime
from utils.doi_utils import doi_from_url
from utils.url_utils import format_display_url

_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')
_MARKET_HISTORY_LIMIT = 10
_SAVED_SEARCH_CHECK_INTERVAL = timedelta(hours=1)


class QmlBridge(QObject):
    """Python backend ve QML arayüzü arasındaki ana köprü controller."""

    # Sinyaller
    isDarkThemeChanged = Signal(bool)
    currentViewChanged = Signal(str)
    isDrawerOpenChanged = Signal(bool)
    selectedResourceChanged = Signal()
    currentReaderResourceChanged = Signal()
    categoriesChanged = Signal()
    tagsChanged = Signal()
    highlightsChanged = Signal()
    vocabularyChanged = Signal()
    statsChanged = Signal()
    urlScraped = Signal(dict)
    readerArticleUpdated = Signal(int, str)
    notificationEmitted = Signal(str, str)  # type (info/error), message
    marketResultsChanged = Signal()
    marketSearchLoadingChanged = Signal(bool)
    marketHistoryChanged = Signal()
    marketDiscoveryChanged = Signal()
    marketSuggestionsChanged = Signal()
    savedSearchesChanged = Signal()
    pdfOutlinesChanged = Signal()
    pdfImportFinished = Signal(bool)  # her importLocalPdf istegi tam bir kez yayar
    activeSavedSearchChanged = Signal()
    savedSearchApplied = Signal(str, "QVariantMap")  # konu, filtreler: QML form alanlarini doldurur
    isSimpleModeChanged = Signal(bool)
    relatedPapersChanged = Signal()

    def __init__(
        self,
        session=None,
        controller: MainController | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        if controller is not None:
            self._controller = controller
        elif session is not None:
            self._controller = MainController(session)
        else:
            raise ValueError("QmlBridge requires either a controller or a session.")

        self._is_dark_theme: bool = True
        self._is_simple_mode: bool = False
        self._current_view: str = "showcase"
        self._is_drawer_open: bool = False
        self._selected_resource: dict = {}
        self._current_reader_resource: dict = {}
        self._categories_cache: list[dict] = []
        self._tags_cache: list[dict] = []
        self._highlights_cache: list[dict] = []
        self._vocabulary_cache: list[dict] = []
        self._stats_cache: dict = {}
        self._market_results_cache: dict = {kind: [] for kind in MARKET_SORTS}
        self._market_meta: dict = {kind: self._blank_market_meta() for kind in MARKET_SORTS}
        self._market_search_loading: bool = False
        # Son arama (sayfalama / "tekrar dene" icin) ve oturum arama gecmisi.
        self._market_topic: str = ""
        self._market_filters = MarketFilters()
        self._market_request_id: int = 0
        self._market_history: list[str] = []
        # Kart altindaki "referanslar / atif yapanlar / benzer / yazar" listeleri ({"tur:kimlik": durum})
        # ve "kutuphaneden oneriler".
        self._market_discovery: dict[str, dict] = {}
        self._market_suggestions: dict = self._empty_suggestions()
        # Kayitli aramalar; calistirilan kayitli arama (yeni yayin sayaci ve koleksiyon etiketi icin).
        self._saved_searches_cache: list[dict] = []
        self._active_saved_search_id: int = 0
        self._saved_searches_checking: bool = False
        # Yerel PDF geometrisi (_highlight_geometry) icin QPdfDocument onbellegi --
        # her highlight/not islemi sonrasi _serialize_resource() cagrildiginda
        # ayni dosyayi tekrar tekrar diskten yuklemeyi (native nesne
        # olusturup yok etmeyi) onler.
        self._pdf_document_cache: dict[str, QPdfDocument] = {}
        # PDF anahatlari (dosya URL'si -> liste) arka planda okunur; yuklenirken anahtar yoktur.
        self._pdf_outlines: dict[str, list] = {}
        self._pdf_outlines_loading: set[str] = set()
        # Kutuphane indeksi onbellegi: kaynak degisince (_reload_resources) gecersiz kilinir.
        self._library_index_cache: LibraryIndex | None = None
        # Toplu islemde kaynak olaylari tek tek yenileme yapmasin (islem sonunda bir kez yenilenir).
        self._resource_events_suspended: bool = False
        # Web PDF'lerinin yerel indirme durumu (bkz. _start_pdf_download).
        self._pdf_downloads_in_progress: set[int] = set()
        self._pdf_download_failed: set[int] = set()
        # Okuyucudaki makalenin referans / atif yapan listeleri (OpenAlex).
        self._related_papers: dict = self._empty_related_papers()

        self._model = ResourceListModel(self)
        self._thread_pool = QThreadPool.globalInstance()

        self._current_filters = {
            "keyword": "",
            "category_id": None,
            "tag_ids": None,
            "statuses": None,
            "favorites_only": False,
        }

        # Event Bus bağlantıları
        event_bus.resource_added.connect(self._on_resource_changed_event)
        event_bus.resource_updated.connect(self._on_resource_changed_event)
        event_bus.resource_deleted.connect(self._on_resource_deleted_event)
        event_bus.highlight_added.connect(lambda: self.reload_highlights())
        event_bus.highlight_deleted.connect(lambda: self.reload_highlights())
        event_bus.vocabulary_added.connect(lambda: self.reload_vocabulary())
        event_bus.vocabulary_deleted.connect(lambda: self.reload_vocabulary())
        # Tum controller'lar basarisizlikta bu sinyali yayiyor (bkz. her
        # *_controller.py'deki except Exception bloklari) ama sinyali dinleyen
        # hicbir yer yoktu -- hatalar sadece log dosyasina gidip kullaniciya
        # hic gorunmuyordu. Merkezi tek baglanti: her controller hatasi artik
        # kirmizi toast olarak yuzeye cikiyor.
        event_bus.error_occurred.connect(lambda msg: self.notificationEmitted.emit("error", msg))
        event_bus.saved_search_changed.connect(self.reload_saved_searches)

        # İlk veri yüklemesi
        self.refresh_all()

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @Property(bool, notify=isDarkThemeChanged)
    def isDarkTheme(self) -> bool:
        return self._is_dark_theme

    @Property(str, notify=currentViewChanged)
    def currentView(self) -> str:
        return self._current_view

    @Property(bool, notify=isDrawerOpenChanged)
    def isDrawerOpen(self) -> bool:
        return self._is_drawer_open

    @Property(dict, notify=selectedResourceChanged)
    def selectedResource(self) -> dict:
        return self._selected_resource

    @Property(dict, notify=currentReaderResourceChanged)
    def currentReaderResource(self) -> dict:
        return self._current_reader_resource

    @Property(QObject, constant=True)
    def resourcesModel(self) -> QObject:
        return self._model

    @Property(list, notify=categoriesChanged)
    def categories(self) -> list:
        return self._categories_cache

    @Property(list, notify=tagsChanged)
    def tags(self) -> list:
        return self._tags_cache

    @Property(list, notify=highlightsChanged)
    def highlights(self) -> list:
        return self._highlights_cache

    @Property(list, constant=True)
    def highlightLabels(self) -> list:
        return HIGHLIGHT_LABELS

    @Property(dict, notify=relatedPapersChanged)
    def relatedPapers(self) -> dict:
        return self._related_papers

    @Property(list, notify=vocabularyChanged)
    def vocabulary(self) -> list:
        return self._vocabulary_cache

    @Property(dict, notify=statsChanged)
    def stats(self) -> dict:
        return self._stats_cache

    @Property(dict, notify=marketResultsChanged)
    def marketResults(self) -> dict:
        return self._market_results_cache

    @Property(dict, notify=marketResultsChanged)
    def marketMeta(self) -> dict:
        """Sekme basina {total, page, hasMore, error, loadingMore} (bkz. marketResults)."""
        return self._market_meta

    @Property(bool, notify=marketSearchLoadingChanged)
    def marketSearchLoading(self) -> bool:
        return self._market_search_loading

    @Property(dict, notify=marketDiscoveryChanged)
    def marketDiscovery(self) -> dict:
        return self._market_discovery

    @Property(dict, notify=pdfOutlinesChanged)
    def pdfOutlines(self) -> dict:
        """Yuklenmis PDF anahatlari: {dosya URL'si: [{title, level, page}]}; yuklenmemisse anahtar yoktur."""
        return self._pdf_outlines

    @Property(list, notify=savedSearchesChanged)
    def savedSearches(self) -> list:
        return self._saved_searches_cache

    @Property(int, notify=activeSavedSearchChanged)
    def activeSavedSearchId(self) -> int:
        return self._active_saved_search_id

    @Property(dict, notify=marketSuggestionsChanged)
    def marketSuggestions(self) -> dict:
        return self._market_suggestions

    @Property(list, notify=marketHistoryChanged)
    def marketSearchHistory(self) -> list:
        return self._market_history

    @Property(bool, notify=isSimpleModeChanged)
    def isSimpleMode(self) -> bool:
        return self._is_simple_mode

    # ------------------------------------------------------------------ #
    # Slots - Temel Navigasyon & Tema
    # ------------------------------------------------------------------ #

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

    @Slot(int)
    def selectResource(self, resource_id: int) -> None:
        resource = self._controller.get_resource(resource_id)
        if resource:
            self._selected_resource = self._serialize_resource(resource)
            self._is_drawer_open = True
            self.selectedResourceChanged.emit()
            self.isDrawerOpenChanged.emit(True)

    @Slot()
    def closeDrawer(self) -> None:
        if self._is_drawer_open:
            self._is_drawer_open = False
            self.isDrawerOpenChanged.emit(False)

    # ------------------------------------------------------------------ #
    # Slots - Kaynak İşlemleri
    # ------------------------------------------------------------------ #

    @Slot(int)
    def togglePin(self, resource_id: int) -> None:
        if not self._controller.toggle_pin(resource_id):
            return
        self._reload_resources()
        self._update_selected_if_matches(resource_id)

    @Slot(int)
    def toggleFavorite(self, resource_id: int) -> None:
        if not self._controller.toggle_favorite(resource_id):
            return
        self._reload_resources()
        self._update_selected_if_matches(resource_id)

    @Slot(int, str)
    def updateResourceStatus(self, resource_id: int, status_str: str) -> None:
        try:
            status = ResourceStatus[status_str]
        except KeyError:
            status = ResourceStatus.PLANNED
        if self._controller.update_resource(resource_id, {"status": status}) is None:
            return
        self._reload_resources()
        self._update_selected_if_matches(resource_id)

    @Slot(int, str)
    def updateResourceNotes(self, resource_id: int, notes: str) -> None:
        if self._controller.update_resource(resource_id, {"content": notes}) is None:
            return
        self._reload_resources()
        self._update_selected_if_matches(resource_id)
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_NOTES_SAVED)

    @Slot(int)
    def deleteResource(self, resource_id: int) -> None:
        if self._selected_resource.get("id") == resource_id:
            self.closeDrawer()
        if self._current_reader_resource.get("id") == resource_id:
            self.closeReader()
        resource = self._controller.get_resource(resource_id)
        pdf_urls = self._owned_pdf_urls(resource) if resource else []
        if not self._controller.delete_resource(resource_id):
            return
        self._pdf_download_failed.discard(resource_id)
        self._reload_resources()
        for pdf_url in pdf_urls:
            self._cleanup_local_pdf(pdf_url)
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_RESOURCE_DELETED)

    def _owned_pdf_urls(self, r: Resource) -> list[str]:
        """Kaynaga bagli, uygulamanin depoladigi yerel PDF dosyalari (file:// URI)."""
        urls = []
        if r.url and r.url.startswith("file://") and r.url.lower().endswith(".pdf"):
            urls.append(r.url)
        local = (r.extra_metadata or {}).get("local_pdf")
        if local:
            urls.append(Path(local).as_uri())
        return urls

    def _cleanup_local_pdf(self, url: str) -> None:
        """Kaynak silinince ilgili QPdfDocument onbellek girdisini ve --
        sadece bizim kopyaladigimiz (pdf_storage_dir icindeki) dosyayi --
        diskten temizler. Kullanicinin kendi dosyalarina asla dokunmaz."""
        if self._pdf_outlines.pop(url, None) is not None:
            self.pdfOutlinesChanged.emit()
        cached_doc = self._pdf_document_cache.pop(url, None)
        if cached_doc is not None and hasattr(cached_doc, "close"):
            # Windows'ta QPdfDocument dosyayi kilitler (WinError 32): close() tek
            # basina yetmez, nesne yok edilmeli. deleteLater() olay dongusune
            # birakilir -- QCoreApplication.sendPostedEvents(None, DeferredDelete)
            # ile zorla flush etmek QML nesnelerini guvenli olmayan anda silip
            # uygulamayi cokertiyordu (segfault, canli dogrulandi).
            cached_doc.close()
            cached_doc.deleteLater()
            del cached_doc
        if not (url.startswith("file://") and url.lower().endswith(".pdf")):
            return
        local_path = Path(QUrl(url).toLocalFile() or url)
        if pdf_storage_dir() in local_path.resolve().parents:
            self._unlink_with_retry(local_path, attempts=6)

    def _unlink_with_retry(self, path: Path, attempts: int) -> None:
        """QML tarafindaki PdfDocument/PdfPageImage'lar dosyayi okuyucu kapandiktan
        kisa sure sonra birakiyor (Windows kilidi, WinError 32) -- ilk deneme
        basarisiz olursa aralikla tekrar denenir."""
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            if attempts <= 1:
                log.warning("Yerel PDF dosyasi silinemedi: %s - %s", path, exc)
                return
            QTimer.singleShot(700, lambda: self._unlink_with_retry(path, attempts - 1))

    @Slot(dict)
    def saveResource(self, data: dict) -> None:
        """Yeni kaynak ekler veya mevcudu günceller."""
        resource_id = data.get("id")
        
        status_val = data.get("status", "INBOX")
        try:
            status_enum = ResourceStatus[status_val]
        except Exception:
            status_enum = ResourceStatus.INBOX

        tag_names = []
        if "tag_names" in data:
            tag_names = [str(t) for t in data["tag_names"]]
        elif "tag_ids" in data and data["tag_ids"]:
            tag_id_set = set(data["tag_ids"])
            tag_names = [t["name"] for t in self._tags_cache if t["id"] in tag_id_set]

        try:
            category_id = int(data["category_id"]) if data.get("category_id") else None
            priority = int(data.get("priority", 2))
        except (TypeError, ValueError):
            self.notificationEmitted.emit("error", AppStrings.NOTIFICATION_INVALID_FORM_DATA)
            return

        payload = {
            "title": data.get("title", "").strip(),
            "url": data.get("url", "").strip() or None,
            "category_id": category_id,
            "status": status_enum,
            "priority": priority,
            "content": data.get("content", ""),
            "tag_names": tag_names,
        }

        old_url = None
        old_pdf_urls: list[str] = []
        had_local_pdf = False
        if resource_id:
            old_resource = self._controller.get_resource(int(resource_id))
            old_url = old_resource.url if old_resource else None
            if old_resource:
                old_pdf_urls = self._owned_pdf_urls(old_resource)
                had_local_pdf = "local_pdf" in (old_resource.extra_metadata or {})
            res = self._controller.update_resource(int(resource_id), payload)
            action_text = AppStrings.NOTIFICATION_ACTION_UPDATED
        else:
            res = self._controller.add_resource(payload)
            action_text = AppStrings.NOTIFICATION_ACTION_SAVED
            if res and res.url:
                # Otomatik arka plan metadata çekimi
                self._schedule_scrape(res.id, res.url)

        if res is None:
            return

        # Duzenlemede URL degistiyse/kaldirildiysa, eski URL bizim kopyaladigimiz
        # bir yerel PDF'e isaret ediyorsa dosyasi/onbellek girdisi oksuz kalirdi.
        if old_url and old_url != (res.url or None):
            for pdf_url in old_pdf_urls:
                self._cleanup_local_pdf(pdf_url)
            self._pdf_download_failed.discard(res.id)
            if had_local_pdf:
                metadata = {k: v for k, v in (res.extra_metadata or {}).items() if k != "local_pdf"}
                self._controller.update_resource(res.id, {"extra_metadata": metadata})

        self._reload_resources()
        self.selectResource(res.id)
        self.notificationEmitted.emit(
            "info",
            AppStrings.NOTIFICATION_RESOURCE_SAVED_FMT.format(action=action_text),
        )

    @Slot(str)
    def scrapeUrl(self, url: str) -> None:
        """Yeni ekleme formundayken URL'den otomatik başlık/açıklama/görsel çeker."""
        clean_url = url.strip()
        if not clean_url:
            self.urlScraped.emit({})
            return
        worker = _ScrapeWorker(0, clean_url)
        worker.signals.finished.connect(lambda _id, meta: self.urlScraped.emit(meta or {}))
        self._thread_pool.start(worker)

    # ------------------------------------------------------------------ #
    # Slots - Okuyucu (Reader)
    # ------------------------------------------------------------------ #

    @Slot(int)
    def openReader(self, resource_id: int) -> None:
        resource = self._controller.get_resource(resource_id)
        if not resource:
            return

        self._current_reader_resource = self._serialize_resource(resource)
        self.currentReaderResourceChanged.emit()
        if self._pdf_file_url(resource):
            self.setCurrentView("pdfReader")
        elif looks_like_remote_pdf(resource.url) and resource.id not in self._pdf_download_failed:
            # Web PDF'i: once yerel diske indirilir, sonra native okuyucuda acilir.
            self.setCurrentView("pdfReader")
            self._start_pdf_download(resource)
        else:
            self.setCurrentView("reader")
        self.closeDrawer()

        # Eğer tam metin boşsa ve url varsa arka planda çıkar. İndirilecek web
        # PDF'inde çıkarım indirme bitince yerel dosyadan yapılır (çift indirme yok).
        awaiting_download = resource.id in self._pdf_downloads_in_progress
        if not resource.full_text and resource.url and not awaiting_download:
            self._schedule_full_text_extract(resource.id, self._pdf_file_url(resource) or resource.url)

    @Slot()
    def closeReader(self) -> None:
        self._current_reader_resource = {}
        self.currentReaderResourceChanged.emit()
        self.setCurrentView("showcase")

    @Slot(int)
    def openTextReader(self, resource_id: int) -> None:
        """Native PDF okuyucudan duz metin okuyucusuna gecis (indirme basarisiz
        olunca ya da kullanici isteyince)."""
        self._pdf_download_failed.add(resource_id)
        self._refresh_reader_resource(resource_id)
        self.setCurrentView("reader")

    def _pdf_file_url(self, r: Resource) -> str | None:
        """Kaynagin native okuyucuda acilabilecek yerel PDF dosyasi (file:// URI).

        Ya kaynagin kendisi yerel PDF'tir ya da web PDF'inin indirilmis
        kopyasi `extra_metadata["local_pdf"]` altinda tutulur."""
        if r.url and r.url.startswith("file://") and r.url.lower().endswith(".pdf"):
            return r.url
        local = (r.extra_metadata or {}).get("local_pdf")
        if local and Path(local).is_file():
            return Path(local).as_uri()
        return None

    def _start_pdf_download(self, resource: Resource) -> None:
        if resource.id in self._pdf_downloads_in_progress or not resource.url:
            return
        self._pdf_downloads_in_progress.add(resource.id)
        worker = _PdfDownloadWorker(resource.id, resource.url, pdf_storage_dir())
        worker.signals.finished.connect(self._on_pdf_download_finished)
        self._thread_pool.start(worker)

    def _on_pdf_download_finished(self, resource_id: int, path: str | None) -> None:
        self._pdf_downloads_in_progress.discard(resource_id)
        is_open = self._current_reader_resource.get("id") == resource_id
        if path:
            resource = self._controller.get_resource(resource_id)
            if resource is None:
                Path(path).unlink(missing_ok=True)
                return
            metadata = dict(resource.extra_metadata or {})
            metadata["local_pdf"] = path
            if self._controller.update_resource(resource_id, {"extra_metadata": metadata}) is None:
                Path(path).unlink(missing_ok=True)
                return
            self._reload_resources()
            self._update_selected_if_matches(resource_id)
            if is_open:
                self._refresh_reader_resource(resource_id)
            if not resource.full_text:
                self._schedule_full_text_extract(resource_id, Path(path).as_uri())
            return
        self._pdf_download_failed.add(resource_id)
        resource = self._controller.get_resource(resource_id)
        if resource and resource.url and not resource.full_text:
            # Metin okuyucusu icin tam metin yine de cikarilmali.
            self._schedule_full_text_extract(resource_id, resource.url)
        if is_open:
            self.notificationEmitted.emit("error", AppStrings.NOTIFICATION_PDF_DOWNLOAD_FAILED)
            self._refresh_reader_resource(resource_id)
            self.setCurrentView("reader")

    @Slot(int, str, str, int, int, int)
    def addHighlight(
        self,
        resource_id: int,
        content: str,
        color: str = "#B45309",
        page: int = -1,
        startIndex: int = -1,
        length: int = -1,
    ) -> None:
        if not content.strip():
            return
        result = self._controller.create_highlight(
            resource_id,
            content.strip(),
            color,
            page if page >= 0 else None,
            startIndex if startIndex >= 0 else None,
            length if length >= 0 else None,
        )
        if result is None:
            return  # Hata zaten event_bus.error_occurred uzerinden toast olarak gosterildi
        self.reload_highlights()
        self._refresh_reader_resource(resource_id)
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_HIGHLIGHT_SAVED)

    @Slot(int, str, int, float, float, float, float, str)
    def addPdfHighlight(
        self,
        resource_id: int,
        file_url: str,
        page: int,
        from_x: float,
        from_y: float,
        to_x: float,
        to_y: float,
        color: str,
    ) -> None:
        """QML'den `QPdfSelection` donen metotlar (getSelection/getSelectionAtIndex)
        cagrilamiyor -- "Unknown method return type: QPdfSelection" (calisma
        zamaninda dogrulandi). Bu yuzden secim noktalarini (page-point uzayinda)
        Python'a tasiyip QPdfDocument islemlerini burada yapiyoruz.
        """
        doc = self._load_pdf_document(file_url)
        if doc is None:
            return
        selection = doc.getSelection(page, QPointF(from_x, from_y), QPointF(to_x, to_y))
        if not selection.isValid() or not selection.text().strip():
            return
        start_index = selection.startIndex()
        length = selection.endIndex() - selection.startIndex()
        result = self._controller.create_highlight(
            resource_id, sanitize_utf8(selection.text()), color, page, start_index, length
        )
        if result is None:
            return
        self.reload_highlights()
        self._refresh_reader_resource(resource_id)
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_HIGHLIGHT_SAVED)

    @Slot(int, str)
    def updateHighlightColor(self, highlight_id: int, color: str) -> None:
        if self._controller.update_highlight_color(highlight_id, color) is None:
            return
        self.reload_highlights()
        if self._current_reader_resource:
            self._refresh_reader_resource(self._current_reader_resource["id"])

    @Slot(int, str)
    def updateHighlightComment(self, highlight_id: int, comment: str) -> None:
        if self._controller.update_highlight_comment(highlight_id, comment) is None:
            return
        self.reload_highlights()
        if self._current_reader_resource:
            self._refresh_reader_resource(self._current_reader_resource["id"])

    @Slot(int)
    def deleteHighlight(self, highlight_id: int) -> None:
        if not self._controller.delete_highlight(highlight_id):
            return
        self.reload_highlights()
        if self._current_reader_resource:
            self._refresh_reader_resource(self._current_reader_resource["id"])
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_HIGHLIGHT_DELETED)

    @Slot("QVariantList")
    def deleteHighlights(self, highlight_ids: list) -> None:
        """Secili alintilari toplu siler (tek yenileme, tek bildirim)."""
        deleted = self._controller.delete_highlights([int(i) for i in highlight_ids])
        if not deleted:
            return
        self.reload_highlights()
        if self._current_reader_resource:
            self._refresh_reader_resource(self._current_reader_resource["id"])
        self.notificationEmitted.emit(
            "info", AppStrings.NOTIFICATION_HIGHLIGHTS_DELETED_FMT.format(count=deleted)
        )

    @Slot(int, str, str, str)
    def addVocabulary(self, resource_id: int, word: str, translation: str, context_sentence: str = "") -> None:
        if not word.strip() or not translation.strip():
            return
        result = self._controller.create_vocabulary(
            resource_id, word.strip(), translation.strip(), context_sentence.strip() or None
        )
        if result is None:
            return
        self.reload_vocabulary()
        self.notificationEmitted.emit(
            "info",
            AppStrings.NOTIFICATION_VOCAB_SAVED_FMT.format(word=word),
        )

    @Slot(int)
    def deleteVocabulary(self, vocabulary_id: int) -> None:
        if not self._controller.delete_vocabulary(vocabulary_id):
            return
        self.reload_vocabulary()
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_VOCAB_DELETED)

    # ------------------------------------------------------------------ #
    # Slots - PDF Notu
    # ------------------------------------------------------------------ #

    def _refresh_reader_resource(self, resource_id: int) -> None:
        res = self._controller.get_resource(resource_id)
        if res:
            self._current_reader_resource = self._serialize_resource(res)
            self.currentReaderResourceChanged.emit()

    @Slot(int, int, float, float, str)
    def addPdfNote(self, resource_id: int, page: int, x: float, y: float, text: str) -> None:
        if not text.strip():
            return
        if self._controller.create_pdf_note(resource_id, page, x, y, text.strip()) is None:
            return
        self._refresh_reader_resource(resource_id)

    @Slot(int, str)
    def updatePdfNote(self, note_id: int, text: str) -> None:
        if not text.strip():
            return
        if self._controller.update_pdf_note(note_id, text.strip()) is None:
            return
        if self._current_reader_resource:
            self._refresh_reader_resource(self._current_reader_resource["id"])

    @Slot(int)
    def deletePdfNote(self, note_id: int) -> None:
        if not self._controller.delete_pdf_note(note_id):
            return
        if self._current_reader_resource:
            self._refresh_reader_resource(self._current_reader_resource["id"])

    # ------------------------------------------------------------------ #
    # Slots - Akademik (atif, OpenAlex bilgisi, referans grafigi, disa aktarim)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _empty_related_papers() -> dict:
        blank = {"loading": False, "error": "", "loaded": False, "items": []}
        return {"openalexId": "", "references": dict(blank), "citations": dict(blank)}

    @Slot(str)
    def loadPdfOutline(self, file_url: str) -> None:
        """PDF anahatini arka planda okur (bkz. utils/pdf_outline.py); sonuc `pdfOutlines`'a yazilir.
        Dosya basina bir kez okunur (QML binding'i her alinti/not degisiminde yeniden calisir)."""
        if not file_url or file_url in self._pdf_outlines or file_url in self._pdf_outlines_loading:
            return
        self._pdf_outlines_loading.add(file_url)
        path = Path(QUrl(file_url).toLocalFile() or file_url)
        worker = _PdfOutlineWorker(file_url, path)
        worker.signals.finished.connect(self._on_pdf_outline_loaded)
        self._thread_pool.start(worker)

    def _on_pdf_outline_loaded(self, file_url: str, outline: list) -> None:
        self._pdf_outlines_loading.discard(file_url)
        self._pdf_outlines[file_url] = outline
        self.pdfOutlinesChanged.emit()

    @Slot(int, str, result=str)
    def citationText(self, resource_id: int, style: str) -> str:
        resource = self._controller.get_resource(resource_id)
        if resource is None:
            return ""
        try:
            return CitationService.format(resource.title, resource.extra_metadata or {}, style)
        except ValueError:
            return ""

    @Slot(int, str)
    def copyCitation(self, resource_id: int, style: str) -> None:
        text = self.citationText(resource_id, style)
        if not text:
            return
        QGuiApplication.clipboard().setText(text)
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_CITATION_COPIED_FMT.format(style=style.upper()))

    @Slot(int)
    def fetchPaperMetadata(self, resource_id: int) -> None:
        """Kaynagin yazar/yil/dergi/DOI/OpenAlex bilgisini OpenAlex'ten getirip kaydeder."""
        resource = self._controller.get_resource(resource_id)
        if resource is None:
            return
        metadata = resource.extra_metadata or {}
        doi = metadata.get("doi")
        if not doi:
            doi = doi_from_url(resource.url)
        worker = _PaperMetadataWorker(resource_id, doi, None if doi else resource.title)
        worker.signals.finished.connect(self._on_paper_metadata_finished)
        self._thread_pool.start(worker)

    def _on_paper_metadata_finished(self, resource_id: int, paper, error: str) -> None:
        if error:
            self.notificationEmitted.emit("error", AppStrings.NOTIFICATION_PAPER_LOOKUP_FAILED)
            return
        if paper is None:
            self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_PAPER_NOT_FOUND)
            return
        resource = self._controller.get_resource(resource_id)
        if resource is None:
            return
        merged = {**(resource.extra_metadata or {}), **paper.to_metadata()}
        if self._controller.update_resource(resource_id, {"extra_metadata": merged}) is None:
            return
        self._reload_resources()
        self._update_selected_if_matches(resource_id)
        if self._current_reader_resource.get("id") == resource_id:
            self._refresh_reader_resource(resource_id)
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_PAPER_METADATA_SAVED)

    @Slot(int)
    def loadRelatedPapers(self, resource_id: int) -> None:
        """Okuyucudaki makalenin referanslarini ve ona atif yapanlari (OpenAlex) yukler."""
        resource = self._controller.get_resource(resource_id)
        openalex_id = ((resource.extra_metadata or {}).get("openalex_id") if resource else "") or ""
        self._related_papers = self._empty_related_papers()
        self._related_papers["openalexId"] = openalex_id
        if openalex_id:
            for kind in ("references", "citations"):
                self._related_papers[kind]["loading"] = True
                worker = _RelatedPapersWorker(openalex_id, kind)
                worker.signals.finished.connect(self._on_related_papers_finished)
                self._thread_pool.start(worker)
        self.relatedPapersChanged.emit()

    def _on_related_papers_finished(self, openalex_id: str, kind: str, papers, error: str) -> None:
        if openalex_id != self._related_papers.get("openalexId"):
            return  # Kullanici bu arada baska bir makaleye gecti.
        items = [self._serialize_paper(p) for p in papers]
        if items:
            self._annotate_library(items, self._library_index())
        self._related_papers[kind] = {
            "loading": False,
            "loaded": not error,
            "error": AppStrings.RELATED_PAPERS_LOAD_FAILED if error else "",
            "items": items,
        }
        self.relatedPapersChanged.emit()

    @Slot(int, str)
    def exportResourceMarkdown(self, resource_id: int, file_url: str) -> None:
        resource = self._controller.get_resource(resource_id)
        if resource is None:
            return
        self._write_export(file_url, ExportService.resource_markdown(resource))

    @Slot(str)
    def exportLibraryMarkdown(self, file_url: str) -> None:
        resources = self._controller.load_resources_with_filters({})
        if not any(ExportService.has_content(r) for r in resources):
            self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_EXPORT_EMPTY)
            return
        self._write_export(file_url, ExportService.library_markdown(resources))

    def _write_export(self, file_url: str, content: str, suffix: str = ".md", encoding: str = "utf-8") -> None:
        path = Path(QUrl(file_url).toLocalFile() or file_url)
        if path.suffix.lower() != suffix:
            path = path.with_suffix(path.suffix + suffix) if path.suffix else path.with_suffix(suffix)
        try:
            with path.open("w", encoding=encoding, newline="") as handle:
                handle.write(content)
        except OSError as exc:
            log.warning("Disa aktarim yazilamadi: %s - %s", path, exc)
            self.notificationEmitted.emit("error", AppStrings.NOTIFICATION_EXPORT_FAILED)
            return
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_EXPORT_DONE_FMT.format(name=path.name))

    @Slot(int, str, int, float, float, float, float, str)
    def addPdfVocabulary(
        self,
        resource_id: int,
        file_url: str,
        page: int,
        from_x: float,
        from_y: float,
        to_x: float,
        to_y: float,
        translation: str,
    ) -> None:
        """PDF'te secili kelimeyi, gectigi cumleyle (baglam) birlikte kelime havuzuna ekler.

        QPdfSelection QML'den cagrilamadigi icin (bkz. addPdfHighlight) secim
        noktalari Python'a tasinir; sayfa metninden cumle burada cikarilir.
        """
        doc = self._load_pdf_document(file_url)
        if doc is None:
            return
        selection = doc.getSelection(page, QPointF(from_x, from_y), QPointF(to_x, to_y))
        word = sanitize_utf8(selection.text()).strip() if selection.isValid() else ""
        if not word:
            return
        page_text = sanitize_utf8(doc.getSelectionAtIndex(page, 0, 1_000_000).text())
        start = selection.startIndex()
        length = selection.endIndex() - start
        context = extract_sentence(page_text, start, length)
        self.addVocabulary(resource_id, " ".join(word.split()), translation, context)

    # ------------------------------------------------------------------ #
    # Slots - Makale Market
    # ------------------------------------------------------------------ #

    @staticmethod
    def _blank_market_meta() -> dict:
        return {"total": 0, "page": 0, "hasMore": False, "error": "", "loadingMore": False}

    @Slot(str)
    @Slot(str, "QVariantMap")
    def searchArticles(self, topic: str, filters: dict | None = None) -> None:
        """Konu + filtrelerle yeni arama (uc sekmenin ilk sayfasi). Kullanici elle arama yaptigi
        icin calisan kayitli arama baglami (koleksiyon etiketi, "goruldu" isareti) birakilir."""
        self._set_active_saved_search(0)
        self._start_market_search(topic, MarketFilters.from_dict(filters))

    def _start_market_search(self, topic: str, parsed_filters: MarketFilters) -> None:
        topic = topic.strip()
        if not topic and not parsed_filters.author_id:
            return  # Konu ya da yazar filtresi olmadan arama yapilmaz.
        self._market_topic = topic
        self._market_filters = parsed_filters
        if topic:
            self._remember_market_topic(topic)
        self._market_request_id += 1
        self._market_search_loading = True
        self.marketSearchLoadingChanged.emit(True)
        worker = _MarketSearchWorker(topic, self._market_filters, request_id=self._market_request_id)
        worker.signals.finished.connect(self._on_market_search_finished)
        self._thread_pool.start(worker)

    @Slot(str)
    def loadMoreArticles(self, kind: str) -> None:
        """Bir sekmenin sonraki sayfasini mevcut listeye ekler."""
        meta = self._market_meta.get(kind)
        has_query = bool(self._market_topic or self._market_filters.author_id)
        if meta is None or not has_query or meta["loadingMore"] or not meta["hasMore"]:
            return
        meta.update(loadingMore=True, error="")
        self.marketResultsChanged.emit()
        worker = _MarketSearchWorker(
            self._market_topic,
            self._market_filters,
            kind=kind,
            page=meta["page"] + 1,
            request_id=self._market_request_id,
        )
        worker.signals.finished.connect(self._on_market_page_loaded)
        self._thread_pool.start(worker)

    @staticmethod
    def _empty_suggestions() -> dict:
        return {"loading": False, "loaded": False, "error": "", "items": [], "sourceCount": 0}

    @Slot(str, str)
    def loadDiscovery(self, kind: str, openalex_id: str) -> None:
        """Bir Market kartinin altindaki listeyi (references / citations / similar / author) yukler."""
        key = f"{kind}:{openalex_id}"
        if not openalex_id or self._market_discovery.get(key, {}).get("loaded"):
            return
        if self._market_discovery.get(key, {}).get("loading"):
            return
        self._market_discovery[key] = {"loading": True, "loaded": False, "error": "", "items": []}
        self.marketDiscoveryChanged.emit()
        worker = _RelatedPapersWorker(openalex_id, kind)
        worker.signals.finished.connect(self._on_discovery_finished)
        self._thread_pool.start(worker)

    def _on_discovery_finished(self, openalex_id: str, kind: str, papers, error: str) -> None:
        items = [self._serialize_paper(p) for p in papers]
        if items:
            self._annotate_library(items, self._library_index())
        self._market_discovery[f"{kind}:{openalex_id}"] = {
            "loading": False,
            "loaded": not error,
            "error": AppStrings.RELATED_PAPERS_LOAD_FAILED if error else "",
            "items": items,
        }
        self.marketDiscoveryChanged.emit()

    @Slot()
    def loadLibrarySuggestions(self) -> None:
        """Kutuphanedeki makalelerin ortak referanslarindan "okumadigin" eser onerileri."""
        if self._market_suggestions["loading"]:
            return
        ids = [
            (r.extra_metadata or {}).get("openalex_id")
            for r in self._controller.load_resources_with_filters({})
        ]
        ids = [i for i in ids if i]
        self._market_suggestions = {**self._empty_suggestions(), "loading": bool(ids), "sourceCount": len(ids)}
        self.marketSuggestionsChanged.emit()
        if not ids:
            return
        worker = _ReadingSuggestionWorker(ids)
        worker.signals.finished.connect(self._on_suggestions_finished)
        self._thread_pool.start(worker)

    def _on_suggestions_finished(self, suggestions, error: str) -> None:
        items = []
        for suggestion in suggestions:
            item = self._serialize_paper(suggestion.paper)
            item["citedByLibrary"] = suggestion.cited_by_library
            items.append(item)
        if items:
            self._annotate_library(items, self._library_index())
        self._market_suggestions = {
            "loading": False,
            "loaded": not error,
            "error": AppStrings.RELATED_PAPERS_LOAD_FAILED if error else "",
            "items": items,
            "sourceCount": self._market_suggestions["sourceCount"],
        }
        self.marketSuggestionsChanged.emit()

    # ------------------------------------------------------------------ #
    # Kayitli aramalar ve yeni yayin takibi
    # ------------------------------------------------------------------ #

    def reload_saved_searches(self) -> None:
        self._saved_searches_cache = [self._serialize_saved_search(s) for s in self._controller.load_saved_searches()]
        self.savedSearchesChanged.emit()

    @staticmethod
    def _serialize_saved_search(search) -> dict:
        filters = dict(search.filters or {})
        parts = [search.topic] if search.topic else []
        if filters.get("authorName"):
            parts.append(f"Yazar: {filters['authorName']}")
        return {
            "id": search.id,
            "topic": search.topic,
            "filters": filters,
            "tag": search.tag_name or "",
            "newCount": search.new_count,
            "label": " · ".join(parts) or "Arama",
        }

    @Slot(str, "QVariantMap", str)
    def saveSearch(self, topic: str, filters: dict, tag_name: str) -> None:
        """Gecerli aramayi (konu + filtreler) kaydeder; simdiki ilk sayfa "goruldu" sayilir."""
        seen_ids = [i["openalexId"] for i in self._market_results_cache.get("recent", []) if i["openalexId"]]
        search = self._controller.create_saved_search(topic, filters, tag_name, seen_ids)
        if search is not None:
            self._set_active_saved_search(search.id)  # Gorunen sonuclar bu aramanin sonuclari
            label = self._serialize_saved_search(search)["label"]
            self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_SAVED_SEARCH_SAVED_FMT.format(label=label))

    @Slot(int)
    def deleteSavedSearch(self, search_id: int) -> None:
        if self._controller.delete_saved_search(search_id) and self._active_saved_search_id == search_id:
            self._set_active_saved_search(0)

    @Slot(int)
    def runSavedSearch(self, search_id: int) -> None:
        """Kayitli aramayi calistirir: QML form alanlari doldurulur, sonuclar "goruldu" isaretlenir ve
        bu arama sirasinda kaydedilen makaleler aramanin koleksiyon etiketini alir."""
        search = next((s for s in self._saved_searches_cache if s["id"] == search_id), None)
        if search is None:
            return
        self._set_active_saved_search(search_id)
        self.savedSearchApplied.emit(search["topic"], search["filters"])
        self._start_market_search(search["topic"], MarketFilters.from_dict(search["filters"]))

    @Slot()
    def checkSavedSearches(self) -> None:
        """Son kontrolu 1 saatten eski kayitli aramalarda yeni yayin var mi diye bakar (arka planda)."""
        if self._saved_searches_checking:
            return
        due = [
            {"id": s.id, "topic": s.topic, "filters": dict(s.filters or {}), "seenIds": list(s.seen_ids or [])}
            for s in self._controller.load_due_saved_searches(_SAVED_SEARCH_CHECK_INTERVAL)
            if s.id != self._active_saved_search_id
        ]
        if not due:
            return
        self._saved_searches_checking = True
        worker = _SavedSearchCheckWorker(due)
        worker.signals.finished.connect(self._on_saved_searches_checked)
        self._thread_pool.start(worker)

    def _on_saved_searches_checked(self, results: list[dict]) -> None:
        self._saved_searches_checking = False
        for result in results:
            if result["error"]:
                continue  # Ag hatasi: sayac ve "son kontrol" degismez, bir sonraki acilista yeniden denenir.
            self._controller.record_saved_search_check(result["id"], result["newCount"])

    def _set_active_saved_search(self, search_id: int) -> None:
        if self._active_saved_search_id != search_id:
            self._active_saved_search_id = search_id
            self.activeSavedSearchChanged.emit()

    def _collection_tag_names(self) -> list[str]:
        search = next((s for s in self._saved_searches_cache if s["id"] == self._active_saved_search_id), None)
        return [search["tag"]] if search and search["tag"] else []

    @Slot()
    def resetMarketResults(self) -> None:
        """Sonuclari temizler (ornegin yazar filtresi kaldirilip konu da bossa)."""
        self._market_request_id += 1  # Gecikmis yanitlar atilsin.
        self._set_active_saved_search(0)
        self._market_results_cache = {kind: [] for kind in MARKET_SORTS}
        self._market_meta = {kind: self._blank_market_meta() for kind in MARKET_SORTS}
        self._market_topic = ""
        self._market_filters = MarketFilters()
        self._market_search_loading = False
        self.marketSearchLoadingChanged.emit(False)
        self.marketResultsChanged.emit()

    @Slot()
    def clearMarketHistory(self) -> None:
        self._market_history = []
        self.marketHistoryChanged.emit()

    def _remember_market_topic(self, topic: str) -> None:
        history = [t for t in self._market_history if t.lower() != topic.lower()]
        self._market_history = [topic, *history][:_MARKET_HISTORY_LIMIT]
        self.marketHistoryChanged.emit()

    @Slot(dict)
    def saveMarketResult(self, paper: dict) -> None:
        """Makale Market sonucunu kaynak olarak kaydeder (bkz. `_save_market_papers`)."""
        self._save_market_papers([paper])

    @Slot(dict)
    def saveMarketResultForLater(self, paper: dict) -> None:
        """"Sonra oku": kaydeder ve `okuma-listesi` etiketiyle isaretler."""
        self._save_market_papers([paper], tag_names=[AppStrings.MARKET_READ_LATER_TAG])

    @Slot("QVariantList")
    def saveMarketResults(self, papers: list) -> None:
        """Secili sonuclari toplu kaydeder (tek yenileme, tek bildirim)."""
        self._save_market_papers(papers, batch=True)

    @staticmethod
    def _market_payload(paper: dict, tag_names: list[str]) -> dict:
        """Market sonucu icin daraltilmis `saveResource` yuku: kategori yok, yazar/yil/atif sayisi
        `extra_metadata`'ya yazilir (formda hic olmayan bir alan)."""
        return {
            "title": (paper.get("title") or "").strip() or "(Baslik yok)",
            "url": paper.get("url") or None,
            "category_id": None,
            "status": ResourceStatus.INBOX,
            "priority": 2,
            "content": None,
            "tag_names": list(tag_names),
            "extra_metadata": {
                key: value
                for key, value in {
                    "authors": paper.get("authors", []),
                    "year": paper.get("year"),
                    "citation_count": paper.get("citationCount", 0),
                    "venue": paper.get("venue"),
                    "doi": paper.get("doi"),
                    "openalex_id": paper.get("openalexId"),
                    "source": "openalex",
                }.items()
                if value not in (None, "", [])
            },
        }

    def _save_market_papers(self, papers: list[dict], tag_names: list[str] | None = None, batch: bool = False) -> None:
        """Kutuphanede olmayan makaleleri kaydeder; olanlari atlar (ayni DOI/OpenAlex kimligi)."""
        index = self._library_index()
        saved, skipped = [], []
        tag_names = [*(tag_names or []), *self._collection_tag_names()]
        self._resource_events_suspended = True  # Her kayit icin liste yenilemek yerine sonda bir kez.
        try:
            for paper in papers:
                doi, openalex_id = paper.get("doi"), paper.get("openalexId")
                if index.find(doi, openalex_id):
                    skipped.append(paper)
                    continue
                res = self._controller.add_resource(self._market_payload(paper, tag_names))
                if res is None:
                    continue  # Hata bildirimi event_bus uzerinden zaten gitti.
                index.add(res.id, doi, openalex_id)
                saved.append(res)
        finally:
            self._resource_events_suspended = False
        if saved:
            self._reload_resources()
            for res in saved:
                if res.url:
                    self._schedule_full_text_extract(res.id, res.url)
        self._notify_market_save(saved, skipped, batch)

    def _notify_market_save(self, saved: list, skipped: list, batch: bool) -> None:
        if batch:
            if saved and skipped:
                message = AppStrings.NOTIFICATION_MARKET_BATCH_SKIPPED_FMT.format(saved=len(saved), skipped=len(skipped))
            elif saved:
                message = AppStrings.NOTIFICATION_MARKET_BATCH_SAVED_FMT.format(saved=len(saved))
            elif skipped:
                message = AppStrings.NOTIFICATION_MARKET_BATCH_ALL_DUPLICATE
            else:
                return
        elif saved:
            message = AppStrings.NOTIFICATION_MARKET_SAVED_FMT.format(title=saved[0].title)
        elif skipped:
            message = AppStrings.NOTIFICATION_MARKET_DUPLICATE_FMT.format(title=skipped[0].get("title", ""))
        else:
            return
        self.notificationEmitted.emit("info", message)

    @Slot(str, str, "QVariantList")
    def exportMarketResults(self, kind: str, file_url: str, papers: list) -> None:
        """Market sonuclarini BibTeX (.bib) ya da CSV (.csv) olarak dosyaya yazar."""
        if not papers:
            self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_MARKET_EXPORT_EMPTY)
            return
        if kind == "bibtex":
            self._write_export(file_url, PaperExportService.bibtex(papers), ".bib")
        elif kind == "csv":
            self._write_export(file_url, PaperExportService.csv(papers), ".csv", encoding="utf-8-sig")
        else:
            raise ValueError(f"Gecersiz disa aktarim turu: {kind}")

    # ------------------------------------------------------------------ #
    # Slots - Yerel PDF İçe Aktarma
    # ------------------------------------------------------------------ #

    @Slot(str)
    def importLocalPdf(self, file_url: str) -> None:
        """Surukle-birak ile gelen yerel bir PDF'i kopyalayip kaynak olarak ekler.

        Orijinal dosyaya dokunulmaz (kopyalanir, tasinmaz/silinmez). Kopyalama arka planda
        yapilir; kaynak tamamlaninca olusturulur. `resources.url` standart bir `file:///...`
        URI'si olarak yazilir -- boylece mevcut okuyucu/extraction altyapisi (ExtractWorker,
        "Tarayicida Ac" butonu) hic degismeden calisir.

        Her cagri sonunda tam bir kez `pdfImportFinished(bool)` yayilir (basari/basarisizlik);
        kaynak-ekle penceresi buna gore kapanir.
        """
        local_path = Path(QUrl(file_url).toLocalFile() or file_url)
        if local_path.suffix.lower() != ".pdf" or not local_path.is_file():
            self.notificationEmitted.emit("error", AppStrings.NOTIFICATION_PDF_IMPORT_INVALID)
            self.pdfImportFinished.emit(False)
            return

        safe_stem = _UNSAFE_FILENAME_CHARS.sub("_", local_path.stem)[:60]
        dest_path = (pdf_storage_dir() / f"{uuid.uuid4().hex[:8]}_{safe_stem}.pdf").resolve()
        worker = _PdfImportWorker(local_path, dest_path)
        worker.signals.finished.connect(self._on_pdf_import_copied)
        self._thread_pool.start(worker)

    def _on_pdf_import_copied(self, source: str, destination: str, error: str) -> None:
        local_path, dest_path = Path(source), Path(destination)
        if error:
            self.notificationEmitted.emit("error", AppStrings.NOTIFICATION_PDF_IMPORT_FAILED)
            self.pdfImportFinished.emit(False)
            return

        payload = {
            "title": local_path.stem,
            "url": dest_path.as_uri(),
            "category_id": None,
            "status": ResourceStatus.INBOX,
            "priority": 2,
            "content": None,
            "tag_names": [],
            "extra_metadata": {"source": "local_pdf", "original_filename": local_path.name},
        }
        res = self._controller.add_resource(payload)
        if res is None:
            # Kaynak olusturma basarisiz oldu (hata zaten toast olarak
            # gosterildi) -- az once kopyalanan dosya oksuz kalmasin.
            dest_path.unlink(missing_ok=True)
            self.pdfImportFinished.emit(False)
            return
        self._reload_resources()
        self._schedule_full_text_extract(res.id, res.url)
        self.notificationEmitted.emit(
            "info", AppStrings.NOTIFICATION_PDF_IMPORTED_FMT.format(title=res.title)
        )
        self.pdfImportFinished.emit(True)

    # ------------------------------------------------------------------ #
    # Slots - Filtreleme & Arama
    # ------------------------------------------------------------------ #

    @Slot(str, str, str, str, bool)
    def applyFilter(
        self,
        keyword: str,
        category_id_str: str,
        tag_id_str: str,
        status_str: str,
        favorite_only: bool,
    ) -> None:
        cat_id = int(category_id_str) if category_id_str and category_id_str != "0" else None
        tag_id = int(tag_id_str) if tag_id_str and tag_id_str != "0" else None
        
        status = None
        if status_str and status_str != "ALL":
            try:
                status = ResourceStatus[status_str]
            except Exception:
                status = None

        statuses = [status] if status else None
        tag_ids = [tag_id] if tag_id else None

        self._current_filters = {
            "keyword": keyword.strip() if keyword else "",
            "category_id": cat_id,
            "tag_ids": tag_ids,
            "statuses": statuses,
            "favorites_only": favorite_only,
        }
        self._reload_resources()

    # ------------------------------------------------------------------ #
    # Slots - Ayarlar (Kategori & Etiket)
    # ------------------------------------------------------------------ #

    @Slot(str, str, str)
    def createCategory(self, name: str, color_hex: str, icon: str = "") -> None:
        if not name.strip():
            return
        result = self._controller.create_category(name.strip(), color_hex.strip() or "#64748B", icon.strip())
        if result is None:
            return
        self.reload_categories()
        self.notificationEmitted.emit(
            "info",
            AppStrings.NOTIFICATION_CATEGORY_ADDED_FMT.format(name=name),
        )

    @Slot(int, str, str, str)
    def updateCategory(self, category_id: int, name: str, color_hex: str, icon: str = "") -> None:
        if not name.strip():
            return
        result = self._controller.update_category(category_id, name.strip(), color_hex.strip(), icon.strip())
        if result is None:
            return
        self.reload_categories()
        self._reload_resources()
        self._refresh_open_panels()
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_CATEGORY_UPDATED)

    @Slot(int)
    def deleteCategory(self, category_id: int) -> None:
        if not self._controller.delete_category(category_id):
            return
        if self._current_filters.get("category_id") == category_id:
            self._current_filters["category_id"] = None
        self.reload_categories()
        self._reload_resources()
        self._refresh_open_panels()
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_CATEGORY_DELETED)

    @Slot(str)
    def createTag(self, name: str) -> None:
        if not name.strip():
            return
        result = self._controller.create_tag(name.strip())
        if result is None:
            return
        self.reload_tags()
        self.notificationEmitted.emit(
            "info",
            AppStrings.NOTIFICATION_TAG_ADDED_FMT.format(name=name),
        )

    @Slot(int, str)
    def updateTag(self, tag_id: int, new_name: str) -> None:
        if not new_name.strip():
            return
        result = self._controller.update_tag(tag_id, new_name.strip())
        if result is None:
            return
        self.reload_tags()
        self._reload_resources()
        self._refresh_open_panels()
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_TAG_UPDATED)

    @Slot(int)
    def deleteTag(self, tag_id: int) -> None:
        if not self._controller.delete_tag(tag_id):
            return
        tag_ids = self._current_filters.get("tag_ids")
        if tag_ids and tag_id in tag_ids:
            self._current_filters["tag_ids"] = None
        self.reload_tags()
        self._reload_resources()
        self._refresh_open_panels()
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_TAG_DELETED)

    @Slot()
    def refresh_all(self) -> None:
        self._reload_resources()
        self.reload_categories()
        self.reload_tags()
        self.reload_highlights()
        self.reload_vocabulary()
        self.reload_saved_searches()

    # ------------------------------------------------------------------ #
    # Dahili Yardımcılar & Worker Yönetimi
    # ------------------------------------------------------------------ #

    def _reload_resources(self) -> None:
        self._library_index_cache = None
        resources = self._controller.load_resources_with_filters(self._current_filters)
        self._model.set_resources(resources)
        self._update_stats()
        self._refresh_library_flags()

    def reload_categories(self) -> None:
        categories = self._controller.load_categories()
        self._categories_cache = [
            {
                "id": c.id,
                "name": c.name,
                "color_hex": c.color_hex or "#64748B",
                "icon": c.icon or "",
                "resource_count": len(c.resources) if hasattr(c, "resources") else 0,
            }
            for c in categories
        ]
        self.categoriesChanged.emit()

    def reload_tags(self) -> None:
        tags = self._controller.load_tags()
        self._tags_cache = [
            {
                "id": t.id,
                "name": t.name,
                "resource_count": len(t.resources) if hasattr(t, "resources") else 0,
            }
            for t in tags
        ]
        self.tagsChanged.emit()

    def reload_highlights(self) -> None:
        highlights = self._controller.load_all_highlights()
        self._highlights_cache = [
            {
                "id": h.id,
                "resource_id": h.resource_id,
                "resource_title": h.resource.title if h.resource else "İsimsiz",
                "content": h.content,
                "color": h.color or "#B45309",
                "label": label_for_color(h.color),
                "comment": h.comment or "",
                "page": h.page_number if h.page_number is not None else -1,
                "created_at": format_local_datetime(h.created_at),
            }
            for h in highlights
        ]
        self.highlightsChanged.emit()

    def reload_vocabulary(self) -> None:
        vocabs = self._controller.load_all_vocabulary()
        self._vocabulary_cache = [
            {
                "id": v.id,
                "resource_id": v.resource_id,
                "resource_title": v.resource.title if v.resource else "İsimsiz",
                "word": v.word,
                "translation": v.translation,
                "context_sentence": v.context_sentence or "",
                "created_at": format_local_datetime(v.created_at),
            }
            for v in vocabs
        ]
        self.vocabularyChanged.emit()

    def _update_stats(self) -> None:
        all_resources = self._controller.load_resources_with_filters({})
        inbox_count = sum(1 for r in all_resources if r.status == ResourceStatus.INBOX)
        planned_count = sum(1 for r in all_resources if r.status == ResourceStatus.PLANNED)
        progress_count = sum(1 for r in all_resources if r.status == ResourceStatus.IN_PROGRESS)
        completed_count = sum(1 for r in all_resources if r.status == ResourceStatus.COMPLETED)
        fav_count = sum(1 for r in all_resources if r.is_favorite)

        self._stats_cache = {
            "total": len(all_resources),
            "inbox": inbox_count,
            "planned": planned_count,
            "in_progress": progress_count,
            "completed": completed_count,
            "favorites": fav_count,
        }
        self.statsChanged.emit()

    def _load_pdf_document(self, file_url: str) -> QPdfDocument | None:
        cached = self._pdf_document_cache.get(file_url)
        if cached is not None:
            return cached
        local_path = QUrl(file_url).toLocalFile() or file_url
        doc = QPdfDocument()
        doc.load(local_path)
        if doc.status() != QPdfDocument.Status.Ready:
            return None
        self._pdf_document_cache[file_url] = doc
        return doc

    def _highlight_geometry(
        self, doc: QPdfDocument, page: int, start_index: int, length: int
    ) -> tuple[list, list] | None:
        selection = doc.getSelectionAtIndex(page, start_index, length)
        if not selection.isValid():
            return None
        polygons = [
            [[point.x(), point.y()] for point in polygon]
            for polygon in selection.bounds()
        ]
        rect = selection.boundingRectangle()
        bounding_rect = [rect.x(), rect.y(), rect.width(), rect.height()]
        return polygons, bounding_rect

    def _serialize_resource(self, r: Resource) -> dict:
        meta = r.extra_metadata or {}
        # Alıntılar listesi -- yerel PDF ise, kalici highlight'lari yeniden
        # cizebilmesi icin geometri (poligon + bounding rect) onceden hesaplanir
        # (QML'den QPdfSelection donen metotlar cagrilamiyor, bkz. addPdfHighlight).
        pdf_file_url = self._pdf_file_url(r)
        pdf_doc = self._load_pdf_document(pdf_file_url) if pdf_file_url else None
        if pdf_file_url:
            pdf_state = "ready"
        elif r.id in self._pdf_downloads_in_progress:
            pdf_state = "downloading"
        elif r.id in self._pdf_download_failed:
            pdf_state = "failed"
        else:
            pdf_state = ""
        hl_list = []
        for h in (r.highlights or []):
            item = {
                "id": h.id,
                "content": h.content,
                "color": h.color or "#B45309",
                "label": label_for_color(h.color),
                "comment": h.comment or "",
                "page": h.page_number if h.page_number is not None else -1,
                "startIndex": h.start_index if h.start_index is not None else -1,
                "length": h.length if h.length is not None else -1,
            }
            if pdf_doc is not None and h.page_number is not None and h.start_index is not None and h.length:
                geometry = self._highlight_geometry(pdf_doc, h.page_number, h.start_index, h.length)
                if geometry is not None:
                    item["boundsPolygons"], item["boundingRect"] = geometry
            hl_list.append(item)

        # Kelimeler listesi
        vocab_list = [
            {"id": v.id, "word": v.word, "translation": v.translation, "context": v.context_sentence or ""}
            for v in (r.vocabulary or [])
        ]

        # PDF notlari (sadece yerel PDF kaynaklarinda anlamli)
        note_list = [
            {"id": n.id, "page": n.page, "x": n.x, "y": n.y, "text": n.note_text}
            for n in (r.pdf_notes or [])
        ]

        return {
            "id": r.id,
            "title": r.title or "",
            "url": r.url or "",
            "domain": format_display_url(r.url) if r.url else "",
            "categoryId": r.category_id or 0,
            "categoryName": r.category.name if r.category else "",
            "categoryColor": r.category.color_hex if r.category and r.category.color_hex else "#64748B",
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "priority": r.priority,
            "isPinned": bool(r.is_pinned),
            "isFavorite": bool(r.is_favorite),
            "content": r.content or "",
            "fullText": r.full_text or "",
            "thumbnailUrl": str(meta.get("image") or meta.get("thumbnail") or ""),
            "description": str(meta.get("description") or ""),
            "readingMinutes": r.reading_minutes or 0,
            "tags": [{"id": t.id, "name": t.name} for t in r.tags],
            "highlights": hl_list,
            "vocabulary": vocab_list,
            "pdfNotes": note_list,
            "pdfFileUrl": pdf_file_url or "",
            "pdfState": pdf_state,
            "paper": {
                "authors": meta.get("authors") or [],
                "year": meta.get("year"),
                "venue": meta.get("venue") or "",
                "doi": meta.get("doi") or "",
                "openalexId": meta.get("openalex_id") or "",
                "citationCount": meta.get("citation_count") or 0,
            },
            "createdAt": format_local_datetime(r.created_at),
        }

    def _serialize_paper(self, paper: PaperResult) -> dict:
        return {
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "citationCount": paper.citation_count,
            "url": paper.url or "",
            "abstract": paper.abstract or "",
            "venue": paper.venue or "",
            "doi": paper.doi or "",
            "openalexId": paper.openalex_id or "",
            "authorIds": paper.author_ids,
            "isOpenAccess": paper.is_open_access,
            "hasPdf": paper.has_pdf,
            "libraryResourceId": 0,
        }

    def _library_index(self) -> LibraryIndex:
        """Kutuphane indeksi; kaynaklar degisene (`_reload_resources`) kadar onbellekte tutulur."""
        if self._library_index_cache is None:
            self._library_index_cache = LibraryIndex(self._controller.load_resources_with_filters({}))
        return self._library_index_cache

    def _annotate_library(self, items: list[dict], index: LibraryIndex) -> bool:
        """Sonuclara kutuphanedeki karsiliginin id'sini (`libraryResourceId`, 0 = yok) yazar;
        herhangi bir deger degistiyse True doner."""
        changed = False
        for item in items:
            match = index.find(item.get("doi"), item.get("openalexId")) or 0
            if item.get("libraryResourceId") != match:
                item["libraryResourceId"] = match
                changed = True
        return changed

    def _refresh_library_flags(self) -> None:
        """Kaynak eklenip silindikce Market/Kaynakca sonuclarindaki "Kutuphanede" durumunu tazeler."""
        market_items = [i for items in self._market_results_cache.values() for i in items]
        related_items = [
            i for kind in ("references", "citations") for i in self._related_papers.get(kind, {}).get("items", [])
        ]
        discovery_items = [i for state in self._market_discovery.values() for i in state["items"]]
        suggestion_items = self._market_suggestions["items"]
        if not (market_items or related_items or discovery_items or suggestion_items):
            return
        index = self._library_index()
        if self._annotate_library(market_items, index):
            self.marketResultsChanged.emit()
        if self._annotate_library(related_items, index):
            self.relatedPapersChanged.emit()
        if self._annotate_library(discovery_items, index):
            self.marketDiscoveryChanged.emit()
        if self._annotate_library(suggestion_items, index):
            self.marketSuggestionsChanged.emit()

    def _market_meta_for(self, page_number: int, page: MarketPage, loaded_count: int) -> dict:
        return {
            "total": page.total,
            "page": page_number,
            "hasMore": not page.error and loaded_count < page.total,
            "error": page.error,
            "loadingMore": False,
        }

    def _on_market_search_finished(self, results: dict[str, MarketPage], request_id: int) -> None:
        if request_id != self._market_request_id:
            return  # Kullanici bu arada yeni bir arama baslatti.
        self._market_results_cache = {
            kind: [self._serialize_paper(p) for p in page.items] for kind, page in results.items()
        }
        self._annotate_library(
            [i for items in self._market_results_cache.values() for i in items], self._library_index()
        )
        self._market_meta = {
            kind: self._market_meta_for(1, page, len(page.items)) for kind, page in results.items()
        }
        self._market_search_loading = False
        self.marketSearchLoadingChanged.emit(False)
        self.marketResultsChanged.emit()
        if self._active_saved_search_id:
            recent_ids = [i["openalexId"] for i in self._market_results_cache.get("recent", []) if i["openalexId"]]
            self._controller.mark_saved_search_seen(self._active_saved_search_id, recent_ids)

    def _on_market_page_loaded(self, results: dict[str, MarketPage], request_id: int) -> None:
        if request_id != self._market_request_id:
            return
        for kind, page in results.items():
            meta = self._market_meta.get(kind)
            if meta is None:
                continue
            if page.error:
                # Mevcut liste korunur; yalnizca "yuklenemedi" bilgisi gosterilir.
                meta.update(loadingMore=False, error=page.error)
                continue
            new_items = [self._serialize_paper(p) for p in page.items]
            self._annotate_library(new_items, self._library_index())
            merged = self._market_results_cache.get(kind, []) + new_items
            self._market_results_cache[kind] = merged
            self._market_meta[kind] = self._market_meta_for(meta["page"] + 1, page, len(merged))
        self.marketResultsChanged.emit()

    def _update_selected_if_matches(self, resource_id: int) -> None:
        if self._selected_resource.get("id") == resource_id:
            res = self._controller.get_resource(resource_id)
            if res:
                self._selected_resource = self._serialize_resource(res)
                self.selectedResourceChanged.emit()

    def _refresh_open_panels(self) -> None:
        """Kategori/etiket adi veya rengi degisince acik olan detay cekmecesi
        (selectedResource) ve okuyucu (currentReaderResource) eski
        kategoriName/categoryColor/tags gostermeye devam ediyordu -- ikisini
        de (acik ise) yeniden serialize eder."""
        if self._selected_resource:
            res = self._controller.get_resource(self._selected_resource["id"])
            if res:
                self._selected_resource = self._serialize_resource(res)
                self.selectedResourceChanged.emit()
        if self._current_reader_resource:
            self._refresh_reader_resource(self._current_reader_resource["id"])

    def _schedule_scrape(self, resource_id: int, url: str) -> None:
        worker = _ScrapeWorker(resource_id, url)
        worker.signals.finished.connect(self._on_scrape_finished)
        self._thread_pool.start(worker)

    def _on_scrape_finished(self, resource_id: int, metadata: dict) -> None:
        if metadata:
            # Mevcut metadata'yi (yazar/yil, local_pdf vb.) ezmeden birlestir.
            existing = self._controller.get_resource(resource_id)
            merged = {**((existing.extra_metadata or {}) if existing else {}), **metadata}
            self._controller.update_resource(resource_id, {"extra_metadata": merged})
            self._reload_resources()
            self._update_selected_if_matches(resource_id)

    def _schedule_full_text_extract(self, resource_id: int, url: str) -> None:
        worker = _ExtractWorker(resource_id, url)
        worker.signals.finished.connect(self._on_extract_finished)
        self._thread_pool.start(worker)

    def _on_extract_finished(self, resource_id: int, full_text: str | None) -> None:
        if full_text:
            self._controller.update_resource(resource_id, {"full_text": full_text})
            if self._current_reader_resource.get("id") == resource_id:
                res = self._controller.get_resource(resource_id)
                if res:
                    self._current_reader_resource = self._serialize_resource(res)
                    self.currentReaderResourceChanged.emit()
                    self.readerArticleUpdated.emit(resource_id, full_text)

    def _on_resource_changed_event(self, resource_id: int) -> None:
        if self._resource_events_suspended:
            return
        self._reload_resources()
        self._update_selected_if_matches(resource_id)

    def _on_resource_deleted_event(self, resource_id: int) -> None:
        self._reload_resources()
        if self._selected_resource.get("id") == resource_id:
            self.closeDrawer()
        if self._current_reader_resource.get("id") == resource_id:
            self.closeReader()
