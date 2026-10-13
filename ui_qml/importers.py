"""Kaynak eklerken arka planda calisan iki yardimci: URL'den metadata cekme ve yerel PDF iceri aktarma.

Sonuc kaynak kayitlari controller uzerinden yazilir; kutuphane listesi/cekmece `resource_*` olaylariyla
(bkz. `LibraryEventRouter`) kendiliginden tazelenir, bu siniflar `LibraryBridge`'i dogrudan cagirmaz.
"""
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal

from core.constants.strings import AppStrings
from core.logger import log
from pdfkit.api import ImportOutcome
from services.metadata_autofill import fill_missing, titles_conflict
from ui_qml.context import BridgeContext
from workers import PaperMetadataWorker, ScrapeWorker


class MetadataScraper(QObject):
    """URL'den baslik/aciklama/gorsel ceker: form onizlemesi (`formScraped`) ve kayit sonrasi arka plan tamamlama."""

    formScraped = Signal(dict)

    def __init__(self, ctx: BridgeContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx

    def scrape_for_form(self, url: str) -> None:
        """Yeni ekleme formundayken URL'den metadata ceker; sonuc `formScraped` ile gelir (bos URL -> {})."""
        clean_url = url.strip()
        if not clean_url:
            self.formScraped.emit({})
            return
        worker = ScrapeWorker(0, clean_url)
        worker.signals.finished.connect(self._on_form_scraped)
        self._ctx.thread_pool.start(worker)

    def _on_form_scraped(self, _resource_id: int, metadata: dict) -> None:
        self.formScraped.emit(metadata or {})

    def schedule(self, resource_id: int, url: str) -> None:
        """Kaydedilmis kaynagin metadata'sini arka planda tamamlar."""
        worker = ScrapeWorker(resource_id, url)
        worker.signals.finished.connect(self._on_scrape_finished)
        self._ctx.thread_pool.start(worker)

    def _on_scrape_finished(self, resource_id: int, metadata: dict) -> None:
        if not metadata:
            return
        # Mevcut metadata'yi (yazar/yil, local_pdf vb.) ezmeden birlestir.
        resources = self._ctx.controllers.resources
        existing = resources.get_resource(resource_id)
        merged = {**((existing.extra_metadata or {}) if existing else {}), **metadata}
        resources.update_resource(resource_id, {"extra_metadata": merged})


class PdfImporter(QObject):
    """Yerel bir PDF'i pdfkit deposuna alip kaynak olarak ekler. Orijinal dosyaya dokunulmaz (kopyalanir).

    Hash, PDFium incelemesi ve kopyalama arka planda yapilir (`PdfLibrary.import_local`); ayni icerik zaten
    kutuphanedeyse ikinci kaynak olusturulmaz. PDF'ten DOI okunabildiyse OpenAlex'ten yazar/yil/dergi bilgisi
    arka planda tamamlanir. Her `import_pdf` cagrisi sonunda tam bir kez `finished(bool)` yayilir."""

    finished = Signal(bool)

    def __init__(self, ctx: BridgeContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        ctx.pdf_library.importFinished.connect(self._on_import_finished)

    def import_pdf(self, file_url: str) -> None:
        local_path = Path(QUrl(file_url).toLocalFile() or file_url)
        if local_path.suffix.lower() != ".pdf" or not local_path.is_file():
            self._ctx.notify.error(AppStrings.NOTIFICATION_PDF_IMPORT_INVALID)
            self.finished.emit(False)
            return
        self._ctx.pdf_library.import_local(local_path)

    def _on_import_finished(self, outcome: ImportOutcome) -> None:
        notify = self._ctx.notify
        if outcome.status == "created":
            self._after_created(outcome)
            self.finished.emit(True)
        elif outcome.status == "duplicate":
            notify.info(AppStrings.NOTIFICATION_PDF_DUPLICATE_FMT.format(title=outcome.title))
            self.finished.emit(True)
        else:
            invalid = outcome.status == "invalid"
            notify.error(
                AppStrings.NOTIFICATION_PDF_IMPORT_INVALID if invalid else AppStrings.NOTIFICATION_PDF_IMPORT_FAILED
            )
            self.finished.emit(False)

    def _after_created(self, outcome: ImportOutcome) -> None:
        resource = self._ctx.controllers.resources.get_resource(outcome.resource_id)
        if resource is not None:
            self._ctx.extractor.schedule(resource.id, resource.url)
        self._ctx.notify.info(AppStrings.NOTIFICATION_PDF_IMPORTED_FMT.format(title=outcome.title))
        inspection = outcome.inspection
        if inspection is not None and not inspection.has_text_layer:
            self._ctx.notify.info(AppStrings.NOTIFICATION_PDF_NO_TEXT_LAYER)
        if inspection is not None and inspection.doi and self._ctx.auto_metadata_enabled():  # Ayarlar > Kunye
            worker = PaperMetadataWorker(outcome.resource_id, inspection.doi, None)
            pdf_title = inspection.title
            worker.signals.finished.connect(
                lambda resource_id, paper, error: self._on_paper_found(resource_id, paper, error, pdf_title)
            )
            self._ctx.thread_pool.start(worker)

    def _on_paper_found(self, resource_id: int, paper, error: str, pdf_title: str | None = None) -> None:
        """DOI ile bulunan OpenAlex kaydini kaynaga isler; bulunamazsa sessiz kalir (kullanici istemedi).

        Yalniz bos alanlar doldurulur. PDF'in gomulu basligi (`pdf_title`) bulunan makalenin basligiyla acikca
        celisiyorsa (DOI metindeki bir atif yapilan makaleye ait olabilir) hicbir sey yazilmaz."""
        if error or paper is None:
            return
        if titles_conflict(pdf_title, paper.title):
            log.info("Kunye doldurma atlandi: bulunan makalenin basligi PDF'in basligiyla celisiyor (id=%d)", resource_id)
            return
        resources = self._ctx.controllers.resources
        resource = resources.get_resource(resource_id)
        if resource is None:
            return
        metadata = resource.extra_metadata or {}
        merged, added = fill_missing(metadata, paper.to_metadata())
        changes: dict = {"extra_metadata": merged} if added else {}
        if paper.title and resource.title == Path(metadata.get("original_filename") or "").stem:
            changes["title"] = paper.title  # Baslik hala dosya adiysa makale basligiyla degistir.
        if changes and resources.update_resource(resource_id, changes) is not None:
            self._ctx.notify.info(AppStrings.NOTIFICATION_PAPER_METADATA_SAVED)
