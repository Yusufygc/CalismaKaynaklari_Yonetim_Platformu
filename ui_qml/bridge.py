import re
import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import Property, QObject, QPointF, QThreadPool, QUrl, Signal, Slot
from PySide6.QtPdf import QPdfDocument

from core.constants.strings import AppStrings
from core.events import event_bus
from core.logger import log
from core.paths import pdf_storage_dir
from models import Resource, ResourceStatus
from controllers.main_controller import MainController
from services.paper_market_service import PaperMarketService, PaperResult
from workers import (
    ExtractWorker as _ExtractWorker,
    MarketSearchWorker as _MarketSearchWorker,
    ScrapeWorker as _ScrapeWorker,
)
from ui_qml.models.resource_list_model import ResourceListModel
from utils.url_utils import format_display_url

_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


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
    isSimpleModeChanged = Signal(bool)

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
        self._market_results_cache: dict = {"recent": [], "popular": [], "cited": []}
        self._market_search_loading: bool = False
        # Yerel PDF geometrisi (_highlight_geometry) icin QPdfDocument onbellegi --
        # her highlight/not islemi sonrasi _serialize_resource() cagrildiginda
        # ayni dosyayi tekrar tekrar diskten yuklemeyi (native nesne
        # olusturup yok etmeyi) onler.
        self._pdf_document_cache: dict[str, QPdfDocument] = {}

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

    @Property(list, notify=vocabularyChanged)
    def vocabulary(self) -> list:
        return self._vocabulary_cache

    @Property(dict, notify=statsChanged)
    def stats(self) -> dict:
        return self._stats_cache

    @Property(dict, notify=marketResultsChanged)
    def marketResults(self) -> dict:
        return self._market_results_cache

    @Property(bool, notify=marketSearchLoadingChanged)
    def marketSearchLoading(self) -> bool:
        return self._market_search_loading

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

    @Slot()
    def toggleSimpleMode(self) -> None:
        self._is_simple_mode = not self._is_simple_mode
        self.isSimpleModeChanged.emit(self._is_simple_mode)

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
        self._controller.toggle_pin(resource_id)
        self._reload_resources()
        self._update_selected_if_matches(resource_id)

    @Slot(int)
    def toggleFavorite(self, resource_id: int) -> None:
        self._controller.toggle_favorite(resource_id)
        self._reload_resources()
        self._update_selected_if_matches(resource_id)

    @Slot(int, str)
    def updateResourceStatus(self, resource_id: int, status_str: str) -> None:
        try:
            status = ResourceStatus[status_str]
        except KeyError:
            status = ResourceStatus.PLANNED
        self._controller.update_resource(resource_id, {"status": status})
        self._reload_resources()
        self._update_selected_if_matches(resource_id)

    @Slot(int, str)
    def updateResourceNotes(self, resource_id: int, notes: str) -> None:
        self._controller.update_resource(resource_id, {"content": notes})
        self._reload_resources()
        self._update_selected_if_matches(resource_id)
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_NOTES_SAVED)

    @Slot(int)
    def deleteResource(self, resource_id: int) -> None:
        if self._selected_resource.get("id") == resource_id:
            self.closeDrawer()
        if self._current_reader_resource.get("id") == resource_id:
            self.closeReader()
        self._controller.delete_resource(resource_id)
        self._reload_resources()
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_RESOURCE_DELETED)

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

        payload = {
            "title": data.get("title", "").strip(),
            "url": data.get("url", "").strip() or None,
            "category_id": int(data["category_id"]) if data.get("category_id") else None,
            "status": status_enum,
            "priority": int(data.get("priority", 2)),
            "content": data.get("content", ""),
            "tag_names": tag_names,
        }

        if resource_id:
            res = self._controller.update_resource(int(resource_id), payload)
            action_text = AppStrings.NOTIFICATION_ACTION_UPDATED
        else:
            res = self._controller.add_resource(payload)
            action_text = AppStrings.NOTIFICATION_ACTION_SAVED
            if res and res.url:
                # Otomatik arka plan metadata çekimi
                self._schedule_scrape(res.id, res.url)

        self._reload_resources()
        if res:
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
        is_local_pdf = bool(resource.url) and resource.url.startswith("file://") and resource.url.lower().endswith(".pdf")
        self.setCurrentView("pdfReader" if is_local_pdf else "reader")
        self.closeDrawer()

        # Eğer tam metin boşsa ve url varsa arka planda çıkar
        if not resource.full_text and resource.url:
            self._schedule_full_text_extract(resource.id, resource.url)

    @Slot()
    def closeReader(self) -> None:
        self._current_reader_resource = {}
        self.currentReaderResourceChanged.emit()
        self.setCurrentView("showcase")

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
        self._controller.create_highlight(
            resource_id,
            content.strip(),
            color,
            page if page >= 0 else None,
            startIndex if startIndex >= 0 else None,
            length if length >= 0 else None,
        )
        self.reload_highlights()
        # Okuyucu içindeki kaynağı tazele
        res = self._controller.get_resource(resource_id)
        if res:
            self._current_reader_resource = self._serialize_resource(res)
            self.currentReaderResourceChanged.emit()
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
        self._controller.create_highlight(resource_id, selection.text(), color, page, start_index, length)
        self.reload_highlights()
        res = self._controller.get_resource(resource_id)
        if res:
            self._current_reader_resource = self._serialize_resource(res)
            self.currentReaderResourceChanged.emit()
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_HIGHLIGHT_SAVED)

    @Slot(int, str)
    def updateHighlightColor(self, highlight_id: int, color: str) -> None:
        self._controller.update_highlight_color(highlight_id, color)
        self.reload_highlights()
        if self._current_reader_resource:
            res = self._controller.get_resource(self._current_reader_resource["id"])
            if res:
                self._current_reader_resource = self._serialize_resource(res)
                self.currentReaderResourceChanged.emit()

    @Slot(int)
    def deleteHighlight(self, highlight_id: int) -> None:
        self._controller.delete_highlight(highlight_id)
        self.reload_highlights()
        if self._current_reader_resource:
            res = self._controller.get_resource(self._current_reader_resource["id"])
            if res:
                self._current_reader_resource = self._serialize_resource(res)
                self.currentReaderResourceChanged.emit()
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_HIGHLIGHT_DELETED)

    @Slot(int, str, str, str)
    def addVocabulary(self, resource_id: int, word: str, translation: str, context_sentence: str = "") -> None:
        if not word.strip() or not translation.strip():
            return
        self._controller.create_vocabulary(
            resource_id, word.strip(), translation.strip(), context_sentence.strip() or None
        )
        self.reload_vocabulary()
        self.notificationEmitted.emit(
            "info",
            AppStrings.NOTIFICATION_VOCAB_SAVED_FMT.format(word=word),
        )

    @Slot(int)
    def deleteVocabulary(self, vocabulary_id: int) -> None:
        self._controller.delete_vocabulary(vocabulary_id)
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
        self._controller.create_pdf_note(resource_id, page, x, y, text.strip())
        self._refresh_reader_resource(resource_id)

    @Slot(int, str)
    def updatePdfNote(self, note_id: int, text: str) -> None:
        if not text.strip():
            return
        self._controller.update_pdf_note(note_id, text.strip())
        if self._current_reader_resource:
            self._refresh_reader_resource(self._current_reader_resource["id"])

    @Slot(int)
    def deletePdfNote(self, note_id: int) -> None:
        self._controller.delete_pdf_note(note_id)
        if self._current_reader_resource:
            self._refresh_reader_resource(self._current_reader_resource["id"])

    # ------------------------------------------------------------------ #
    # Slots - Makale Market
    # ------------------------------------------------------------------ #

    @Slot(str)
    def searchArticles(self, topic: str) -> None:
        topic = topic.strip()
        if not topic:
            return
        self._market_search_loading = True
        self.marketSearchLoadingChanged.emit(True)
        worker = _MarketSearchWorker(topic)
        worker.signals.finished.connect(self._on_market_search_finished)
        self._thread_pool.start(worker)

    @Slot(dict)
    def saveMarketResult(self, paper: dict) -> None:
        """Makale Market sonucunu kaynak olarak kaydeder.

        `saveResource`'un daralti bir kopyasi: market sonucunda kategori/etiket
        gibi kullanici secimleri yok, bunun yerine yazar/yil/atif sayisi
        `extra_metadata`'ya yaziliyor (formda hic olmayan bir alan).
        """
        payload = {
            "title": (paper.get("title") or "").strip() or "(Baslik yok)",
            "url": paper.get("url") or None,
            "category_id": None,
            "status": ResourceStatus.INBOX,
            "priority": 2,
            "content": None,
            "tag_names": [],
            "extra_metadata": {
                "authors": paper.get("authors", []),
                "year": paper.get("year"),
                "citation_count": paper.get("citationCount", 0),
                "source": "openalex",
            },
        }
        res = self._controller.add_resource(payload)
        if res:
            self._reload_resources()
            if res.url:
                self._schedule_full_text_extract(res.id, res.url)
            self.notificationEmitted.emit(
                "info", AppStrings.NOTIFICATION_MARKET_SAVED_FMT.format(title=res.title)
            )

    # ------------------------------------------------------------------ #
    # Slots - Yerel PDF İçe Aktarma
    # ------------------------------------------------------------------ #

    @Slot(str)
    def importLocalPdf(self, file_url: str) -> None:
        """Surukle-birak ile gelen yerel bir PDF'i kopyalayip kaynak olarak ekler.

        Orijinal dosyaya dokunulmaz (kopyalanir, tasinmaz/silinmez).
        `resources.url` standart bir `file:///...` URI'si olarak yazilir --
        boylece mevcut okuyucu/extraction altyapisi (ExtractWorker,
        "Tarayicida Ac" butonu) hic degismeden calisir.
        """
        local_path = Path(QUrl(file_url).toLocalFile() or file_url)
        if local_path.suffix.lower() != ".pdf" or not local_path.is_file():
            self.notificationEmitted.emit("error", AppStrings.NOTIFICATION_PDF_IMPORT_INVALID)
            return

        try:
            safe_stem = _UNSAFE_FILENAME_CHARS.sub("_", local_path.stem)[:60]
            dest_path = (pdf_storage_dir() / f"{uuid.uuid4().hex[:8]}_{safe_stem}.pdf").resolve()
            shutil.copyfile(local_path, dest_path)
        except OSError as exc:
            log.warning("PDF kopyalanamadi: %s - %s", local_path, exc)
            self.notificationEmitted.emit("error", AppStrings.NOTIFICATION_PDF_IMPORT_FAILED)
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
        if res:
            self._reload_resources()
            self._schedule_full_text_extract(res.id, res.url)
            self.notificationEmitted.emit(
                "info", AppStrings.NOTIFICATION_PDF_IMPORTED_FMT.format(title=res.title)
            )

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
        if name.strip():
            self._controller.create_category(name.strip(), color_hex.strip() or "#64748B", icon.strip())
            self.reload_categories()
            self.notificationEmitted.emit(
                "info",
                AppStrings.NOTIFICATION_CATEGORY_ADDED_FMT.format(name=name),
            )

    @Slot(int, str, str, str)
    def updateCategory(self, category_id: int, name: str, color_hex: str, icon: str = "") -> None:
        if name.strip():
            self._controller.update_category(category_id, name.strip(), color_hex.strip(), icon.strip())
            self.reload_categories()
            self._reload_resources()
            self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_CATEGORY_UPDATED)

    @Slot(int)
    def deleteCategory(self, category_id: int) -> None:
        self._controller.delete_category(category_id)
        self.reload_categories()
        self._reload_resources()
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_CATEGORY_DELETED)

    @Slot(str)
    def createTag(self, name: str) -> None:
        if name.strip():
            self._controller.create_tag(name.strip())
            self.reload_tags()
            self.notificationEmitted.emit(
                "info",
                AppStrings.NOTIFICATION_TAG_ADDED_FMT.format(name=name),
            )

    @Slot(int, str)
    def updateTag(self, tag_id: int, new_name: str) -> None:
        if new_name.strip():
            self._controller.update_tag(tag_id, new_name.strip())
            self.reload_tags()
            self._reload_resources()
            self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_TAG_UPDATED)

    @Slot(int)
    def deleteTag(self, tag_id: int) -> None:
        self._controller.delete_tag(tag_id)
        self.reload_tags()
        self._reload_resources()
        self.notificationEmitted.emit("info", AppStrings.NOTIFICATION_TAG_DELETED)

    @Slot()
    def refresh_all(self) -> None:
        self._reload_resources()
        self.reload_categories()
        self.reload_tags()
        self.reload_highlights()
        self.reload_vocabulary()

    # ------------------------------------------------------------------ #
    # Dahili Yardımcılar & Worker Yönetimi
    # ------------------------------------------------------------------ #

    def _reload_resources(self) -> None:
        resources = self._controller.load_resources_with_filters(self._current_filters)
        self._model.set_resources(resources)
        self._update_stats()

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
                "created_at": h.created_at.strftime("%d.%m.%Y %H:%M") if h.created_at else "",
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
                "created_at": v.created_at.strftime("%d.%m.%Y %H:%M") if v.created_at else "",
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
        # Tahmini okuma süresi
        word_count = len((r.full_text or r.content or "").split())
        reading_time = max(1, round(word_count / 200)) if word_count > 0 else 1

        # Alıntılar listesi -- yerel PDF ise, kalici highlight'lari yeniden
        # cizebilmesi icin geometri (poligon + bounding rect) onceden hesaplanir
        # (QML'den QPdfSelection donen metotlar cagrilamiyor, bkz. addPdfHighlight).
        is_local_pdf = bool(r.url) and r.url.startswith("file://") and r.url.lower().endswith(".pdf")
        pdf_doc = self._load_pdf_document(r.url) if is_local_pdf else None
        hl_list = []
        for h in (r.highlights or []):
            item = {
                "id": h.id,
                "content": h.content,
                "color": h.color or "#B45309",
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
            "readingMinutes": reading_time,
            "tags": [{"id": t.id, "name": t.name} for t in r.tags],
            "highlights": hl_list,
            "vocabulary": vocab_list,
            "pdfNotes": note_list,
            "createdAt": r.created_at.strftime("%d.%m.%Y %H:%M") if r.created_at else "",
        }

    def _serialize_paper(self, paper: PaperResult) -> dict:
        return {
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "citationCount": paper.citation_count,
            "url": paper.url or "",
            "abstract": paper.abstract or "",
        }

    def _on_market_search_finished(self, results: dict) -> None:
        self._market_results_cache = {
            key: [self._serialize_paper(p) for p in papers] for key, papers in results.items()
        }
        self._market_search_loading = False
        self.marketSearchLoadingChanged.emit(False)
        self.marketResultsChanged.emit()

    def _update_selected_if_matches(self, resource_id: int) -> None:
        if self._selected_resource.get("id") == resource_id:
            res = self._controller.get_resource(resource_id)
            if res:
                self._selected_resource = self._serialize_resource(res)
                self.selectedResourceChanged.emit()

    def _schedule_scrape(self, resource_id: int, url: str) -> None:
        worker = _ScrapeWorker(resource_id, url)
        worker.signals.finished.connect(self._on_scrape_finished)
        self._thread_pool.start(worker)

    def _on_scrape_finished(self, resource_id: int, metadata: dict) -> None:
        if metadata:
            self._controller.update_resource(resource_id, {"extra_metadata": metadata})
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
        self._reload_resources()
        self._update_selected_if_matches(resource_id)

    def _on_resource_deleted_event(self, resource_id: int) -> None:
        self._reload_resources()
        if self._selected_resource.get("id") == resource_id:
            self.closeDrawer()
        if self._current_reader_resource.get("id") == resource_id:
            self.closeReader()
