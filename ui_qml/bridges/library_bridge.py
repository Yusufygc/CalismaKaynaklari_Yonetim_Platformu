import re
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from core.constants.strings import AppStrings
from core.events import event_bus
from models import Resource, ResourceStatus
from ui_qml.context import BridgeContext
from ui_qml.models.resource_list_model import ResourceListModel
from workers import PdfImportWorker, ScrapeWorker

_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


@dataclass
class _PreviousResource:
    """`saveResource` duzenlemesinden onceki kaynagin temizlik icin gereken bilgileri."""

    url: str | None = None
    pdf_urls: list[str] = field(default_factory=list)
    had_local_pdf: bool = False


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
        self._events_suspended = False
        self._current_filters: dict = {
            "keyword": "",
            "category_id": None,
            "tag_ids": None,
            "statuses": None,
            "favorites_only": False,
        }

        event_bus.resource_added.connect(self._on_resource_changed_event)
        event_bus.resource_updated.connect(self._on_resource_changed_event)
        event_bus.resource_deleted.connect(self._on_resource_deleted_event)
        event_bus.category_updated.connect(self._on_taxonomy_changed)
        event_bus.tag_updated.connect(self._on_taxonomy_changed)
        event_bus.category_deleted.connect(self._on_category_deleted)
        event_bus.tag_deleted.connect(self._on_tag_deleted)

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

    def refresh(self) -> None:
        self.reload()

    def reload(self) -> None:
        """Vitrin listesini (mevcut filtrelerle) ve istatistikleri yeniler; kutuphane indeksi gecersiz olur."""
        self._ctx.library_index.invalidate()
        self._model.set_resources(self._resources.load_resources_with_filters(self._current_filters))
        self._update_stats()
        self.resourcesReloaded.emit()

    def _update_stats(self) -> None:
        all_resources = self._resources.load_resources_with_filters({})
        count_status = lambda status: sum(1 for r in all_resources if r.status == status)  # noqa: E731
        self._stats_cache = {
            "total": len(all_resources),
            "inbox": count_status(ResourceStatus.INBOX),
            "planned": count_status(ResourceStatus.PLANNED),
            "in_progress": count_status(ResourceStatus.IN_PROGRESS),
            "completed": count_status(ResourceStatus.COMPLETED),
            "favorites": sum(1 for r in all_resources if r.is_favorite),
        }
        self.statsChanged.emit()

    @contextmanager
    def suspend_events(self):
        """Toplu islemde her kayit icin liste yenilemek yerine islem sonunda tek `reload()` yapilsin diye
        kaynak olaylarini gecici olarak susturur."""
        self._events_suspended = True
        try:
            yield
        finally:
            self._events_suspended = False

    def update_selected_if_matches(self, resource_id: int) -> None:
        if self._selected_resource.get("id") == resource_id:
            res = self._resources.get_resource(resource_id)
            if res:
                self._selected_resource = self._ctx.serializer.serialize(res)
                self.selectedResourceChanged.emit()

    def refresh_selected(self) -> None:
        """Acik detay cekmecesini (varsa) yeniden serilestirir."""
        if self._selected_resource:
            self.update_selected_if_matches(self._selected_resource["id"])

    # ------------------------------------------------------------------ #
    # Olaylar
    # ------------------------------------------------------------------ #

    def _on_resource_changed_event(self, resource_id: int) -> None:
        if self._events_suspended:
            return
        self.reload()
        self.update_selected_if_matches(resource_id)

    def _on_resource_deleted_event(self, resource_id: int) -> None:
        self.reload()
        if self._selected_resource.get("id") == resource_id:
            self.closeDrawer()

    def _on_taxonomy_changed(self, _id: int) -> None:
        """Kategori/etiket adi veya rengi degisince liste ve acik cekmece eski adi gostermesin."""
        self.reload()
        self.refresh_selected()

    def _on_category_deleted(self, category_id: int) -> None:
        if self._current_filters.get("category_id") == category_id:
            self._current_filters["category_id"] = None
        self._on_taxonomy_changed(category_id)

    def _on_tag_deleted(self, tag_id: int) -> None:
        tag_ids = self._current_filters.get("tag_ids")
        if tag_ids and tag_id in tag_ids:
            self._current_filters["tag_ids"] = None
        self._on_taxonomy_changed(tag_id)

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

        self._current_filters = {
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
        payload = self._parse_form_payload(data)
        if payload is None:
            return

        resource_id = data.get("id")
        previous = self._snapshot_before_edit(int(resource_id)) if resource_id else None
        if resource_id:
            res = self._resources.update_resource(int(resource_id), payload)
            action_text = AppStrings.NOTIFICATION_ACTION_UPDATED
        else:
            res = self._resources.add_resource(payload)
            action_text = AppStrings.NOTIFICATION_ACTION_SAVED
            if res and res.url:
                self._schedule_scrape(res.id, res.url)  # Otomatik arka plan metadata cekimi

        if res is None:
            return
        if previous is not None:
            self._cleanup_replaced_url(previous, res)

        self.reload()
        self.selectResource(res.id)
        self._ctx.notify.info(AppStrings.NOTIFICATION_RESOURCE_SAVED_FMT.format(action=action_text))

    def _parse_form_payload(self, data: dict) -> dict | None:
        """Form verisini controller yukune cevirir; gecersiz sayisal alanda bildirim verip None doner."""
        status = ResourceStatus.__members__.get(data.get("status", "INBOX"), ResourceStatus.INBOX)
        try:
            category_id = int(data["category_id"]) if data.get("category_id") else None
            priority = int(data.get("priority", 2))
        except (TypeError, ValueError):
            self._ctx.notify.error(AppStrings.NOTIFICATION_INVALID_FORM_DATA)
            return None
        return {
            "title": data.get("title", "").strip(),
            "url": data.get("url", "").strip() or None,
            "category_id": category_id,
            "status": status,
            "priority": priority,
            "content": data.get("content", ""),
            "tag_names": self._form_tag_names(data),
        }

    def _form_tag_names(self, data: dict) -> list[str]:
        if "tag_names" in data:
            return [str(t) for t in data["tag_names"]]
        selected_ids = set(data.get("tag_ids") or [])
        return [t.name for t in self._ctx.controllers.tags.load_tags() if t.id in selected_ids]

    def _snapshot_before_edit(self, resource_id: int) -> _PreviousResource:
        """Duzenlemeden onceki URL/yerel PDF bilgisi (URL degisirse eski dosyalar temizlensin diye)."""
        old = self._resources.get_resource(resource_id)
        if old is None:
            return _PreviousResource()
        return _PreviousResource(
            url=old.url,
            pdf_urls=self._ctx.pdf_files.owned_pdf_urls(old),
            had_local_pdf="local_pdf" in (old.extra_metadata or {}),
        )

    def _cleanup_replaced_url(self, previous: _PreviousResource, res: Resource) -> None:
        """Duzenlemede URL degistiyse/kaldirildiysa, eski URL bizim kopyaladigimiz bir yerel PDF'e
        isaret ediyorsa dosyasi/onbellek girdisi oksuz kalirdi."""
        if not previous.url or previous.url == (res.url or None):
            return
        for pdf_url in previous.pdf_urls:
            self._ctx.pdf_files.cleanup_local_pdf(pdf_url)
        self._ctx.pdf_files.clear_failed(res.id)
        if previous.had_local_pdf:
            metadata = {k: v for k, v in (res.extra_metadata or {}).items() if k != "local_pdf"}
            self._resources.update_resource(res.id, {"extra_metadata": metadata})

    # ------------------------------------------------------------------ #
    # URL'den metadata
    # ------------------------------------------------------------------ #

    @Slot(str)
    def scrapeUrl(self, url: str) -> None:
        """Yeni ekleme formundayken URL'den otomatik başlık/açıklama/görsel çeker."""
        clean_url = url.strip()
        if not clean_url:
            self.urlScraped.emit({})
            return
        worker = ScrapeWorker(0, clean_url)
        worker.signals.finished.connect(lambda _id, meta: self.urlScraped.emit(meta or {}))
        self._ctx.thread_pool.start(worker)

    def _schedule_scrape(self, resource_id: int, url: str) -> None:
        worker = ScrapeWorker(resource_id, url)
        worker.signals.finished.connect(self._on_scrape_finished)
        self._ctx.thread_pool.start(worker)

    def _on_scrape_finished(self, resource_id: int, metadata: dict) -> None:
        if not metadata:
            return
        # Mevcut metadata'yi (yazar/yil, local_pdf vb.) ezmeden birlestir.
        existing = self._resources.get_resource(resource_id)
        merged = {**((existing.extra_metadata or {}) if existing else {}), **metadata}
        self._resources.update_resource(resource_id, {"extra_metadata": merged})
        self.reload()
        self.update_selected_if_matches(resource_id)

    # ------------------------------------------------------------------ #
    # Yerel PDF iceri aktarma
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
            self._ctx.notify.error(AppStrings.NOTIFICATION_PDF_IMPORT_INVALID)
            self.pdfImportFinished.emit(False)
            return

        safe_stem = _UNSAFE_FILENAME_CHARS.sub("_", local_path.stem)[:60]
        dest_path = (self._ctx.pdf_files.storage_dir() / f"{uuid.uuid4().hex[:8]}_{safe_stem}.pdf").resolve()
        worker = PdfImportWorker(local_path, dest_path)
        worker.signals.finished.connect(self._on_pdf_import_copied)
        self._ctx.thread_pool.start(worker)

    def _on_pdf_import_copied(self, source: str, destination: str, error: str) -> None:
        local_path, dest_path = Path(source), Path(destination)
        if error:
            self._ctx.notify.error(AppStrings.NOTIFICATION_PDF_IMPORT_FAILED)
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
        res = self._resources.add_resource(payload)
        if res is None:
            # Kaynak olusturma basarisiz oldu (hata zaten toast olarak
            # gosterildi) -- az once kopyalanan dosya oksuz kalmasin.
            dest_path.unlink(missing_ok=True)
            self.pdfImportFinished.emit(False)
            return
        self.reload()
        self._ctx.extractor.schedule(res.id, res.url)
        self._ctx.notify.info(AppStrings.NOTIFICATION_PDF_IMPORTED_FMT.format(title=res.title))
        self.pdfImportFinished.emit(True)
