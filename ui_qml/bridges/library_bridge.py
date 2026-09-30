from contextlib import contextmanager

from PySide6.QtCore import Property, QObject, Signal, Slot

from core.constants.strings import AppStrings
from models import ResourceStatus
from ui_qml.context import BridgeContext
from ui_qml.importers import MetadataScraper, PdfImporter
from ui_qml.library_events import LibraryEventRouter
from ui_qml.models.resource_list_model import ResourceListModel
from ui_qml.resource_form import ResourceFormHandler


def _library_stats(resources: list) -> dict:
    """Kenar cubugu sayaclari: toplam, durum bazinda ve favori sayilari."""
    by_status = {status: 0 for status in ResourceStatus}
    for resource in resources:
        by_status[resource.status] = by_status.get(resource.status, 0) + 1
    return {
        "total": len(resources),
        "inbox": by_status[ResourceStatus.INBOX],
        "planned": by_status[ResourceStatus.PLANNED],
        "in_progress": by_status[ResourceStatus.IN_PROGRESS],
        "completed": by_status[ResourceStatus.COMPLETED],
        "favorites": sum(1 for r in resources if r.is_favorite),
    }


class LibraryBridge(QObject):
    """Kaynak kutuphanesi: vitrin listesi/filtreleri, detay cekmecesi, kaynak ekleme-duzenleme-silme,
    yerel PDF iceri aktarma ve istatistikler."""

    selectedResourceChanged = Signal()
    isDrawerOpenChanged = Signal(bool)
    statsChanged = Signal()
    urlScraped = Signal(dict)
    pdfImportFinished = Signal(bool)  # her importLocalPdf istegi tam bir kez yayar
    resourcesReloaded = Signal()  # Liste yenilendi (diger bridge'ler kutuphane bayraklarini tazeler)

    def __init__(self, ctx: BridgeContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._resources = ctx.controllers.resources
        self._model = ResourceListModel(self)
        self._selected_resource: dict = {}
        self._is_drawer_open = False
        self._stats_cache: dict = {}
        # Acik alanlar (bridge disindan `LibraryEventRouter` ve `MarketSaver` kullanir).
        self.events_suspended = False
        self.filters: dict = {
            "keyword": "",
            "category_id": None,
            "tag_ids": None,
            "statuses": None,
            "favorites_only": False,
        }
        self._form = ResourceFormHandler(ctx)
        self._scraper = MetadataScraper(ctx, self)
        self._scraper.formScraped.connect(self.urlScraped)
        self._importer = PdfImporter(ctx, self)
        self._importer.finished.connect(self.pdfImportFinished)
        LibraryEventRouter(self)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @Property(QObject, constant=True)
    def resourcesModel(self) -> QObject:
        return self._model

    @Property(dict, notify=selectedResourceChanged)
    def selectedResource(self) -> dict:
        return self._selected_resource

    @Property(bool, notify=isDrawerOpenChanged)
    def isDrawerOpen(self) -> bool:
        return self._is_drawer_open

    @Property(dict, notify=statsChanged)
    def stats(self) -> dict:
        return self._stats_cache

    # ------------------------------------------------------------------ #
    # Yukleme / yenileme
    # ------------------------------------------------------------------ #

    def reload(self) -> None:
        """Vitrin listesini (mevcut filtrelerle) ve istatistikleri yeniler; kutuphane indeksi gecersiz olur."""
        self._ctx.library_index.invalidate()
        self._model.set_resources(self._resources.load_resources_with_filters(self.filters))
        self._stats_cache = _library_stats(self._resources.load_resources_with_filters({}))
        self.statsChanged.emit()
        self.resourcesReloaded.emit()

    @contextmanager
    def suspend_events(self):
        """Toplu islemde her kayit icin liste yenilemek yerine islem sonunda tek `reload()` yapilsin diye
        kaynak olaylarini gecici olarak susturur."""
        self.events_suspended = True
        try:
            yield
        finally:
            self.events_suspended = False

    def update_selected_if_matches(self, resource_id: int | None = None) -> None:
        """Acik cekmece `resource_id` kaynagindaysa (verilmezse acik olan kaynak icin) yeniden serilestirir."""
        selected_id = self._selected_resource.get("id")
        if selected_id is None or (resource_id is not None and resource_id != selected_id):
            return
        res = self._resources.get_resource(selected_id)
        if res:
            self._selected_resource = self._ctx.serializer.serialize(res)
            self.selectedResourceChanged.emit()

    # ------------------------------------------------------------------ #
    # Cekmece / secim
    # ------------------------------------------------------------------ #

    @Slot(int)
    def selectResource(self, resource_id: int) -> None:
        resource = self._resources.get_resource(resource_id)
        if resource:
            self._selected_resource = self._ctx.serializer.serialize(resource)
            self._is_drawer_open = True
            self.selectedResourceChanged.emit()
            self.isDrawerOpenChanged.emit(True)

    @Slot()
    def closeDrawer(self) -> None:
        if self._is_drawer_open:
            self._is_drawer_open = False
            self.isDrawerOpenChanged.emit(False)

    # ------------------------------------------------------------------ #
    # Filtreleme
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
        category_id = int(category_id_str) if category_id_str and category_id_str != "0" else None
        tag_id = int(tag_id_str) if tag_id_str and tag_id_str != "0" else None
        status = None
        if status_str and status_str != "ALL":
            status = ResourceStatus.__members__.get(status_str)

        self.filters = {
            "keyword": keyword.strip() if keyword else "",
            "category_id": category_id,
            "tag_ids": [tag_id] if tag_id else None,
            "statuses": [status] if status else None,
            "favorites_only": favorite_only,
        }
        self.reload()

    # ------------------------------------------------------------------ #
    # Kaynak islemleri
    # ------------------------------------------------------------------ #

    @Slot(int)
    def togglePin(self, resource_id: int) -> None:
        if self._resources.toggle_pin(resource_id):
            self.reload()
            self.update_selected_if_matches(resource_id)

    @Slot(int)
    def toggleFavorite(self, resource_id: int) -> None:
        if self._resources.toggle_favorite(resource_id):
            self.reload()
            self.update_selected_if_matches(resource_id)

    @Slot(int, str)
    def updateResourceStatus(self, resource_id: int, status_str: str) -> None:
        status = ResourceStatus.__members__.get(status_str, ResourceStatus.PLANNED)
        if self._resources.update_resource(resource_id, {"status": status}) is None:
            return
        self.reload()
        self.update_selected_if_matches(resource_id)

    @Slot(int, str)
    def updateResourceNotes(self, resource_id: int, notes: str) -> None:
        if self._resources.update_resource(resource_id, {"content": notes}) is None:
            return
        self.reload()
        self.update_selected_if_matches(resource_id)
        self._ctx.notify.info(AppStrings.NOTIFICATION_NOTES_SAVED)

    @Slot(int)
    def deleteResource(self, resource_id: int) -> None:
        if self._selected_resource.get("id") == resource_id:
            self.closeDrawer()
        resource = self._resources.get_resource(resource_id)
        pdf_urls = self._ctx.pdf_files.owned_pdf_urls(resource) if resource else []
        # Acik okuyucu `resource_deleted` olayini dinleyip kendini kapatir (bkz. ReaderBridge).
        if not self._resources.delete_resource(resource_id):
            return
        self._ctx.pdf_files.clear_failed(resource_id)
        self.reload()
        for pdf_url in pdf_urls:
            self._ctx.pdf_files.cleanup_local_pdf(pdf_url)
        self._ctx.notify.info(AppStrings.NOTIFICATION_RESOURCE_DELETED)

    @Slot(dict)
    def saveResource(self, data: dict) -> None:
        """Yeni kaynak ekler veya mevcudu günceller."""
        payload = self._form.parse_payload(data)
        if payload is None:
            return

        resource_id = data.get("id")
        previous = self._form.snapshot(int(resource_id)) if resource_id else None
        if resource_id:
            res = self._resources.update_resource(int(resource_id), payload)
            action_text = AppStrings.NOTIFICATION_ACTION_UPDATED
        else:
            res = self._resources.add_resource(payload)
            action_text = AppStrings.NOTIFICATION_ACTION_SAVED
            if res and res.url:
                self._scraper.schedule(res.id, res.url)  # Otomatik arka plan metadata cekimi

        if res is None:
            return
        if previous is not None:
            self._form.cleanup_replaced_url(previous, res)

        self.reload()
        self.selectResource(res.id)
        self._ctx.notify.info(AppStrings.NOTIFICATION_RESOURCE_SAVED_FMT.format(action=action_text))

    @Slot(str)
    def scrapeUrl(self, url: str) -> None:
        """Yeni ekleme formundayken URL'den otomatik başlık/açıklama/görsel çeker (sonuç `urlScraped`)."""
        self._scraper.scrape_for_form(url)

    @Slot(str)
    def importLocalPdf(self, file_url: str) -> None:
        """Surukle-birak ile gelen yerel bir PDF'i kopyalayip kaynak olarak ekler (bkz. `PdfImporter`).
        Her cagri sonunda tam bir kez `pdfImportFinished(bool)` yayilir."""
        self._importer.import_pdf(file_url)
