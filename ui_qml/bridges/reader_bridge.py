from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from core.constants.strings import AppStrings
from core.events import event_bus
from services.export_service import ExportService
from services.pdf_download_service import looks_like_remote_pdf
from ui_qml.bridges.library_bridge import LibraryBridge
from ui_qml.context import BridgeContext
from ui_qml.file_export import write_export
from workers import PdfOutlineWorker


class ReaderBridge(QObject):
    """Okuyucu: HTML/PDF acma-kapama, PDF indirme, PDF anahati ve Markdown disa aktarimi. Alinti/kelime/not
    `AnnotationsBridge`'de, atif ve OpenAlex bilgisi `CitationsBridge`'dedir."""

    currentReaderResourceChanged = Signal()
    pdfOutlinesChanged = Signal()
    readerArticleUpdated = Signal(int, str)

    def __init__(
        self,
        ctx: BridgeContext,
        library: LibraryBridge,
        navigate: Callable[[str], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._library = library
        self._navigate = navigate  # Kok bridge'in `setCurrentView`'i: hangi sayfanin gorunecegi orada tutulur.
        self._current: dict = {}
        # PDF anahatlari (dosya URL'si -> liste) arka planda okunur; yuklenirken anahtar yoktur.
        self._pdf_outlines: dict[str, list] = {}
        self._pdf_outlines_loading: set[str] = set()

        ctx.pdf_files.downloadFinished.connect(self._on_pdf_download_finished)
        ctx.pdf_files.documentReleased.connect(self._on_document_released)
        ctx.extractor.extracted.connect(self._on_full_text_extracted)
        event_bus.resource_deleted.connect(self._on_resource_deleted)
        for signal in (event_bus.category_updated, event_bus.category_deleted,
                       event_bus.tag_updated, event_bus.tag_deleted):
            signal.connect(self._on_taxonomy_changed)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @Property(dict, notify=currentReaderResourceChanged)
    def currentReaderResource(self) -> dict:
        return self._current

    @Property(dict, notify=pdfOutlinesChanged)
    def pdfOutlines(self) -> dict:
        """Yuklenmis PDF anahatlari: {dosya URL'si: [{title, level, page}]}; yuklenmemisse anahtar yoktur."""
        return self._pdf_outlines

    # ------------------------------------------------------------------ #
    # Yukleme / olaylar
    # ------------------------------------------------------------------ #

    def _on_resource_deleted(self, resource_id: int) -> None:
        if self._current.get("id") == resource_id:
            self.closeReader()

    def _on_taxonomy_changed(self, _id: int) -> None:
        """Kategori/etiket adi ya da rengi degisince acik okuyucu eski adi gostermesin."""
        self.refresh_current()

    def refresh_current(self, resource_id: int | None = None) -> None:
        """Acik okuyucu kaynagini (varsa) yeniden serilestirir. `resource_id` verilirse o kaynak icin."""
        target_id = resource_id if resource_id is not None else self._current.get("id")
        if not target_id:
            return
        res = self._ctx.controllers.resources.get_resource(target_id)
        if res:
            self._current = self._ctx.serializer.serialize(res)
            self.currentReaderResourceChanged.emit()

    def refresh_if_open(self, resource_id: int) -> None:
        """`resource_id` su an okuyucuda aciksa yeniden serilestirir."""
        if self._current.get("id") == resource_id:
            self.refresh_current(resource_id)

    # ------------------------------------------------------------------ #
    # Okuyucuyu ac/kapat
    # ------------------------------------------------------------------ #

    @Slot(int)
    def openReader(self, resource_id: int) -> None:
        resource = self._ctx.controllers.resources.get_resource(resource_id)
        if not resource:
            return

        pdf_files = self._ctx.pdf_files
        self._current = self._ctx.serializer.serialize(resource)
        self.currentReaderResourceChanged.emit()
        if pdf_files.pdf_file_url(resource):
            self._navigate("pdfReader")
        elif looks_like_remote_pdf(resource.url) and not pdf_files.has_failed(resource.id):
            # Web PDF'i: once yerel diske indirilir, sonra native okuyucuda acilir.
            self._navigate("pdfReader")
            pdf_files.start_download(resource)
        else:
            self._navigate("reader")
        self._library.closeDrawer()

        # Eger tam metin bossa ve url varsa arka planda cikar. Indirilecek web
        # PDF'inde cikarim indirme bitince yerel dosyadan yapilir (cift indirme yok).
        if not resource.full_text and resource.url and not pdf_files.is_downloading(resource.id):
            self._ctx.extractor.schedule(resource.id, pdf_files.pdf_file_url(resource) or resource.url)

    @Slot()
    def closeReader(self) -> None:
        self._current = {}
        self.currentReaderResourceChanged.emit()
        self._navigate("showcase")

    @Slot(int)
    def openTextReader(self, resource_id: int) -> None:
        """Native PDF okuyucudan duz metin okuyucusuna gecis (indirme basarisiz
        olunca ya da kullanici isteyince)."""
        self._ctx.pdf_files.mark_failed(resource_id)
        self.refresh_current(resource_id)
        self._navigate("reader")

    def _on_pdf_download_finished(self, resource_id: int, path: str | None) -> None:
        if path:
            self._on_pdf_downloaded(resource_id, path)
        else:
            self._on_pdf_download_failed(resource_id)

    def _on_pdf_downloaded(self, resource_id: int, path: str) -> None:
        resources = self._ctx.controllers.resources
        resource = resources.get_resource(resource_id)
        if resource is None:
            Path(path).unlink(missing_ok=True)
            return
        metadata = dict(resource.extra_metadata or {})
        metadata["local_pdf"] = path
        if resources.update_resource(resource_id, {"extra_metadata": metadata}) is None:
            Path(path).unlink(missing_ok=True)
            return
        self._library.reload()
        self._library.update_selected_if_matches(resource_id)
        if self._current.get("id") == resource_id:
            self.refresh_current(resource_id)
        if not resource.full_text:
            self._ctx.extractor.schedule(resource_id, Path(path).as_uri())

    def _on_pdf_download_failed(self, resource_id: int) -> None:
        self._ctx.pdf_files.mark_failed(resource_id)
        resource = self._ctx.controllers.resources.get_resource(resource_id)
        if resource and resource.url and not resource.full_text:
            # Metin okuyucusu icin tam metin yine de cikarilmali.
            self._ctx.extractor.schedule(resource_id, resource.url)
        if self._current.get("id") == resource_id:
            self._ctx.notify.error(AppStrings.NOTIFICATION_PDF_DOWNLOAD_FAILED)
            self.refresh_current(resource_id)
            self._navigate("reader")

    def _on_full_text_extracted(self, resource_id: int, full_text: str) -> None:
        if self._current.get("id") == resource_id:
            self.refresh_current(resource_id)
            self.readerArticleUpdated.emit(resource_id, full_text)

    def _on_document_released(self, file_url: str) -> None:
        if self._pdf_outlines.pop(file_url, None) is not None:
            self.pdfOutlinesChanged.emit()

    # ------------------------------------------------------------------ #
    # PDF anahati
    # ------------------------------------------------------------------ #

    @Slot(str)
    def loadPdfOutline(self, file_url: str) -> None:
        """PDF anahatini arka planda okur (bkz. utils/pdf_outline.py); sonuc `pdfOutlines`'a yazilir.
        Dosya basina bir kez okunur (QML binding'i her alinti/not degisiminde yeniden calisir)."""
        if not file_url or file_url in self._pdf_outlines or file_url in self._pdf_outlines_loading:
            return
        self._pdf_outlines_loading.add(file_url)
        path = Path(QUrl(file_url).toLocalFile() or file_url)
        worker = PdfOutlineWorker(file_url, path)
        worker.signals.finished.connect(self._on_pdf_outline_loaded)
        self._ctx.thread_pool.start(worker)

    def _on_pdf_outline_loaded(self, file_url: str, outline: list) -> None:
        self._pdf_outlines_loading.discard(file_url)
        self._pdf_outlines[file_url] = outline
        self.pdfOutlinesChanged.emit()

    # ------------------------------------------------------------------ #
    # Markdown disa aktarim
    # ------------------------------------------------------------------ #

    @Slot(int, str)
    def exportResourceMarkdown(self, resource_id: int, file_url: str) -> None:
        resource = self._ctx.controllers.resources.get_resource(resource_id)
        if resource is None:
            return
        write_export(file_url, ExportService.resource_markdown(resource), self._ctx.notify)

    @Slot(str)
    def exportLibraryMarkdown(self, file_url: str) -> None:
        resources = self._ctx.controllers.resources.load_resources_with_filters({})
        if not any(ExportService.has_content(r) for r in resources):
            self._ctx.notify.info(AppStrings.NOTIFICATION_EXPORT_EMPTY)
            return
        write_export(file_url, ExportService.library_markdown(resources), self._ctx.notify)
