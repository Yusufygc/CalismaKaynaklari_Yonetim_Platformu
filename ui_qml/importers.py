"""Kaynak eklerken arka planda calisan iki yardimci: URL'den metadata cekme ve yerel PDF iceri aktarma.

Sonuc kaynak kayitlari controller uzerinden yazilir; kutuphane listesi/cekmece `resource_*` olaylariyla
(bkz. `LibraryEventRouter`) kendiliginden tazelenir, bu siniflar `LibraryBridge`'i dogrudan cagirmaz.
"""
import re
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal

from core.constants.strings import AppStrings
from models import ResourceStatus
from ui_qml.context import BridgeContext
from workers import PdfImportWorker, ScrapeWorker

_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


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
    """Yerel bir PDF'i kopyalayip kaynak olarak ekler. Orijinal dosyaya dokunulmaz (kopyalanir, tasinmaz/silinmez).

    Kopyalama arka planda yapilir; kaynak tamamlaninca olusturulur. `resources.url` standart bir `file:///...`
    URI'si olarak yazilir -- boylece mevcut okuyucu/extraction altyapisi degismeden calisir. Her `import_pdf`
    cagrisi sonunda tam bir kez `finished(bool)` yayilir (basari/basarisizlik).
    """

    finished = Signal(bool)

    def __init__(self, ctx: BridgeContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx

    def import_pdf(self, file_url: str) -> None:
        local_path = Path(QUrl(file_url).toLocalFile() or file_url)
        if local_path.suffix.lower() != ".pdf" or not local_path.is_file():
            self._ctx.notify.error(AppStrings.NOTIFICATION_PDF_IMPORT_INVALID)
            self.finished.emit(False)
            return

        safe_stem = _UNSAFE_FILENAME_CHARS.sub("_", local_path.stem)[:60]
        dest_path = (self._ctx.pdf_files.storage_dir() / f"{uuid.uuid4().hex[:8]}_{safe_stem}.pdf").resolve()
        worker = PdfImportWorker(local_path, dest_path)
        worker.signals.finished.connect(self._on_copied)
        self._ctx.thread_pool.start(worker)

    def _on_copied(self, source: str, destination: str, error: str) -> None:
        local_path, dest_path = Path(source), Path(destination)
        if error:
            self._ctx.notify.error(AppStrings.NOTIFICATION_PDF_IMPORT_FAILED)
            self.finished.emit(False)
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
        res = self._ctx.controllers.resources.add_resource(payload)
        if res is None:
            # Kaynak olusturma basarisiz oldu (hata zaten toast olarak gosterildi) -- kopya oksuz kalmasin.
            dest_path.unlink(missing_ok=True)
            self.finished.emit(False)
            return
        self._ctx.extractor.schedule(res.id, res.url)
        self._ctx.notify.info(AppStrings.NOTIFICATION_PDF_IMPORTED_FMT.format(title=res.title))
        self.finished.emit(True)
