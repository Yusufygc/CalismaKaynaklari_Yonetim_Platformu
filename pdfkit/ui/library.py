import re
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThreadPool, QTimer, Signal
from sqlalchemy.orm import Session

from core.logger import log
from pdfkit.app.annotations import AnnotationService
from pdfkit.app.documents import DocumentService
from pdfkit.app.legacy_import import LegacyAnnotationImporter, LegacyImportReport
from pdfkit.app.importing import prepare_pdf, prepare_remote_pdf
from pdfkit.app.ports import LegacyPdf, ResourceCatalogPort
from pdfkit.domain.errors import NotAPdfError
from pdfkit.domain.models import Document, PdfInspection, PreparedPdf
from pdfkit.infra.downloader import Fetch
from pdfkit.infra.file_store import FileStore
from pdfkit.ui.workers import CallWorker, submit

_MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
_ADOPT_CHUNK = 5  # her olay dongusu turunda islenen eski PDF sayisi (UI donmasin)


@dataclass(frozen=True)
class ImportOutcome:
    status: str  # "created" | "duplicate" | "invalid" | "failed"
    resource_id: int | None = None
    document: Document | None = None
    inspection: PdfInspection | None = None
    title: str = ""


class PdfLibrary(QObject):
    """PDF belge yasam dongusu (Qt cephesi): yerel ice aktarma, uzak PDF indirme, eski dosyalarin depoya alinmasi
    ve cop toplama. Agir isler (hash, PDFium incelemesi, kopyalama, indirme) havuz thread'inde, veritabani
    yazimi ana thread'de yapilir. Oturum yalnizca ana thread'de kullanilir."""

    importFinished = Signal(object)  # ImportOutcome
    downloadFinished = Signal(int, object)  # kaynak kimligi, depodaki dosya yolu (Path) | None
    legacyAdoptionFinished = Signal(int)  # depoya alinan eski PDF sayisi

    def __init__(
        self,
        session: Session,
        storage_dir: Callable[[], Path],
        catalog: ResourceCatalogPort,
        thread_pool: Callable[[], QThreadPool],
        fetch: Fetch,
        max_download_bytes: int = _MAX_DOWNLOAD_BYTES,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._storage_dir = storage_dir
        self._catalog = catalog
        self._thread_pool = thread_pool
        self._fetch = fetch
        self._max_download_bytes = max_download_bytes
        self._adopt_queue: deque = deque()
        self._adopted = 0
        self.legacyAdoptionFinished.connect(self._after_adoption)

    # ------------------------------------------------------------------ #
    # Yardimcilar
    # ------------------------------------------------------------------ #

    def store(self) -> FileStore:
        return FileStore(self._storage_dir())

    def documents(self) -> DocumentService:
        return DocumentService(self._session, self.store())

    def annotations(self) -> AnnotationService:
        return AnnotationService(self._session)

    def _run(self, fn: Callable[[], Any], callback: Callable[[Any, Exception | None], None]) -> None:
        submit(self._thread_pool(), CallWorker(fn, callback), self._dispatch)

    def _dispatch(self, callback: Callable[[Any, Exception | None], None], result: Any, error: Any) -> None:
        callback(result, error)

    def owns(self, path: Path) -> bool:
        """`path` pdfkit deposundaki bir dosya mi? (Silme gibi islemler depo dosyalarini dogrudan silmemeli.)"""
        return self.store().contains(path)

    def file_path(self, document: Document) -> Path:
        return self.store().absolute(document.rel_path)

    # ------------------------------------------------------------------ #
    # Yerel ice aktarma
    # ------------------------------------------------------------------ #

    def import_local(self, source: Path) -> None:
        """Yerel PDF'i depoya alir ve kaynak olarak ekler; sonuc `importFinished(ImportOutcome)` ile gelir."""
        store = self.store()
        self._run(lambda: prepare_pdf(source, store), self._on_import_prepared)

    def _on_import_prepared(self, prepared: PreparedPdf | None, error: Exception | None) -> None:
        if error is not None or prepared is None:
            status = "invalid" if isinstance(error, NotAPdfError) else "failed"
            self.importFinished.emit(ImportOutcome(status))
            return
        service = self.documents()
        title = prepared.inspection.title or Path(prepared.original_filename or "belge").stem
        existing = service.find_by_sha(prepared.stored.sha256)
        linked = service.resources_with_document(existing.id) if existing else []
        if linked:
            self.importFinished.emit(ImportOutcome("duplicate", linked[0], existing, prepared.inspection, title))
            return

        file_url = service.store.absolute(prepared.stored.rel_path).as_uri()
        resource_id = self._catalog.create_pdf_resource(
            title, file_url, {"source": "local_pdf", "original_filename": prepared.original_filename}
        )
        if resource_id is None:
            self._discard_unregistered(service, prepared)
            self.importFinished.emit(ImportOutcome("failed", title=title))
            return
        document = None
        try:
            document = service.register(prepared, resource_id, "local")
        except Exception:  # Kaynak olustu; belge kaydi sonraki acilista `adopt_legacy` ile tamamlanir.
            log.warning("Belge kaydi sonraya birakildi: resource_id=%d", resource_id)
        self.importFinished.emit(ImportOutcome("created", resource_id, document, prepared.inspection, title))

    @staticmethod
    def _discard_unregistered(service: DocumentService, prepared: PreparedPdf) -> None:
        """Kaydi olusmayan yeni dosyayi karantinaya alir (baska belgenin dosyasina dokunmaz)."""
        if prepared.stored.created and service.find_by_sha(prepared.stored.sha256) is None:
            service.store.quarantine(prepared.stored.rel_path)

    # ------------------------------------------------------------------ #
    # Uzak PDF indirme
    # ------------------------------------------------------------------ #

    def download_remote(self, resource_id: int, url: str) -> None:
        """Web PDF'ini akis halinde indirip depoya alir; sonuc `downloadFinished(kaynak, yol | None)`."""
        store = self.store()
        self._run(
            lambda: prepare_remote_pdf(url, store, fetch=self._fetch, max_bytes=self._max_download_bytes),
            partial(self._on_download_prepared, resource_id),
        )

    def _on_download_prepared(self, resource_id: int, prepared: PreparedPdf | None, error: Exception | None) -> None:
        if error is not None or prepared is None:
            self.downloadFinished.emit(resource_id, None)
            return
        service = self.documents()
        try:
            service.register(prepared, resource_id, "web")
        except Exception:
            self._discard_unregistered(service, prepared)
            self.downloadFinished.emit(resource_id, None)
            return
        self.downloadFinished.emit(resource_id, service.store.absolute(prepared.stored.rel_path))

    # ------------------------------------------------------------------ #
    # Eski dosyalarin depoya alinmasi
    # ------------------------------------------------------------------ #

    def adopt_legacy(self) -> None:
        """Eski duzendeki (uuid onekli, depo kokunde) PDF'leri icerik adresli depoya alir ve kaynaklari yeni
        dosyaya yonlendirir. Hash/kopyalama arka planda, kayit guncellemeleri kucuk dilimlerle ana thread'de."""
        service = self.documents()
        linked = service.linked_resource_ids()
        pending = [item for item in self._catalog.legacy_pdfs() if item.resource_id not in linked]
        if not pending:
            self.legacyAdoptionFinished.emit(0)
            return
        store = service.store
        self._run(lambda: self._prepare_legacy(pending, store), self._on_legacy_prepared)

    @staticmethod
    def _prepare_legacy(items: list[LegacyPdf], store: FileStore) -> list[tuple[LegacyPdf, PreparedPdf | None]]:
        results = []
        for item in items:
            try:
                prepared = None
                if item.path.is_file():
                    prepared = prepare_pdf(item.path, store, original_filename=_legacy_display_name(item.path))
            except Exception as exc:
                log.warning("Eski PDF depoya alinamadi: %s - %s", item.path, exc)
                prepared = None
            results.append((item, prepared))
        return results

    def _on_legacy_prepared(self, results: list | None, error: Exception | None) -> None:
        if error is not None or not results:
            self.legacyAdoptionFinished.emit(0)
            return
        self._adopt_queue = deque(results)
        self._adopted = 0
        self._adopt_next()

    def _adopt_next(self) -> None:
        service = self.documents()
        for _ in range(_ADOPT_CHUNK):
            if not self._adopt_queue:
                break
            item, prepared = self._adopt_queue.popleft()
            if prepared is not None and self._adopt_one(service, item, prepared):
                self._adopted += 1
        if self._adopt_queue:
            QTimer.singleShot(0, self._adopt_next)
            return
        log.info("Eski PDF'lerin depoya alinmasi bitti: %d dosya.", self._adopted)
        self.legacyAdoptionFinished.emit(self._adopted)

    def _adopt_one(self, service: DocumentService, item: LegacyPdf, prepared: PreparedPdf) -> bool:
        new_path = service.store.absolute(prepared.stored.rel_path)
        try:
            service.register(prepared, item.resource_id, "local")
        except Exception:
            return False
        if new_path != item.path and not self._catalog.repoint(item, new_path):
            return False
        # Eski (uuid onekli) dosya artik hicbir kaynaga bagli degil; `PdfStorageService.sweep_orphans` bir
        # sonraki acilista karantinaya alir (kullanicinin kendi dosyalarina hicbir zaman dokunulmaz).
        return True

    # ------------------------------------------------------------------ #
    # Cop toplama
    # ------------------------------------------------------------------ #

    def collect_garbage(self, attempts: int = 1, interval_ms: int = 700) -> None:
        """Baglantisiz belgeleri karantinaya alir. Windows'ta acik PDF kilitli olabilir: tasinamayan belge
        varsa `attempts` kez, `interval_ms` arayla yeniden denenir."""
        report = self.documents().collect_garbage()
        if report.pending and attempts > 1:
            QTimer.singleShot(interval_ms, partial(self.collect_garbage, attempts - 1, interval_ms))
        elif report.pending:
            log.warning("%d PDF belgesi kilitli, sonraki acilista yeniden denenecek.", report.pending)

    def start_maintenance(self) -> None:
        """Acilista: cop toplama + eski PDF'leri depoya alma (bitince eski alinti/not/kelime kopyalanir)."""
        self.collect_garbage()
        self.adopt_legacy()

    # ------------------------------------------------------------------ #
    # Eski alinti / not / kelime kayitlarinin kopyalanmasi
    # ------------------------------------------------------------------ #

    def import_legacy_annotations(self, delete_missing: bool = True) -> LegacyImportReport:
        """Eski tablolardaki PDF kayitlarini pdfkit tablolarina esitler (bkz. `LegacyAnnotationImporter`)."""
        return LegacyAnnotationImporter(self._session).run(delete_missing)

    def _after_adoption(self, _adopted: int) -> None:
        try:
            self.import_legacy_annotations()
        except Exception:  # Acilisi engellemez; hata zaten loglandi, sonraki acilista yeniden denenir.
            log.warning("Eski PDF kayitlarinin kopyalanmasi atlandi.")


def _legacy_display_name(path: Path) -> str:
    """Eski duzendeki `<8 hex>_ad.pdf` dosya adindan okunur adi cikarir."""
    return re.sub(r"^[0-9a-f]{8}_", "", path.name)
