"""Yerel PDF dosyalari: URL cozumleme, QPdfDocument onbellegi/geometri, web PDF indirme durumu, temizlik.

Reader (okuyucu), Library (kaynak silme/duzenleme) ve serilestirici ortak kullanir; bu yuzden
kopya/durum tek yerde tutulur. Kaynak guncelleme gibi is kurallari burada DEGIL, indirme
sonucunu isleyen `ReaderBridge`'dedir.
"""
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QPointF, QTimer, QUrl, Signal
from PySide6.QtPdf import QPdfDocument

from core.logger import log
from core.paths import pdf_storage_dir
from models import Resource
from utils.text_utils import sanitize_utf8
from workers import PdfDownloadWorker

if TYPE_CHECKING:
    from ui_qml.context import BridgeContext


class PdfFileManager(QObject):
    downloadFinished = Signal(int, object)  # kaynak id, yerel dosya yolu (str) | None
    documentReleased = Signal(str)  # onbellekten dusen dosya URL'si (anahat onbellegi gibi turevler temizlensin)

    def __init__(self, ctx: "BridgeContext", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        # Yerel PDF geometrisi (highlight_geometry) icin QPdfDocument onbellegi -- her alinti/not
        # islemi sonrasi kaynak serilestirildiginde ayni dosyayi tekrar tekrar diskten yuklemeyi
        # (native nesne olusturup yok etmeyi) onler.
        self._document_cache: dict[str, QPdfDocument] = {}
        # Web PDF'lerinin yerel indirme durumu.
        self._downloads_in_progress: set[int] = set()
        self._download_failed: set[int] = set()

    # ------------------------------------------------------------------ #
    # URL / durum
    # ------------------------------------------------------------------ #

    @staticmethod
    def storage_dir() -> Path:
        return pdf_storage_dir()

    @staticmethod
    def pdf_file_url(resource: Resource) -> str | None:
        """Kaynagin native okuyucuda acilabilecek yerel PDF dosyasi (file:// URI).

        Ya kaynagin kendisi yerel PDF'tir ya da web PDF'inin indirilmis
        kopyasi `extra_metadata["local_pdf"]` altinda tutulur."""
        if resource.url and resource.url.startswith("file://") and resource.url.lower().endswith(".pdf"):
            return resource.url
        local = (resource.extra_metadata or {}).get("local_pdf")
        if local and Path(local).is_file():
            return Path(local).as_uri()
        return None

    @staticmethod
    def owned_pdf_urls(resource: Resource) -> list[str]:
        """Kaynaga bagli, uygulamanin depoladigi yerel PDF dosyalari (file:// URI)."""
        urls = []
        if resource.url and resource.url.startswith("file://") and resource.url.lower().endswith(".pdf"):
            urls.append(resource.url)
        local = (resource.extra_metadata or {}).get("local_pdf")
        if local:
            urls.append(Path(local).as_uri())
        return urls

    def state(self, resource: Resource, pdf_file_url: str | None) -> str:
        """Kaynagin yerel PDF durumu: ready | downloading | failed | '' (PDF degil)."""
        if pdf_file_url:
            return "ready"
        if resource.id in self._downloads_in_progress:
            return "downloading"
        if resource.id in self._download_failed:
            return "failed"
        return ""

    def is_downloading(self, resource_id: int) -> bool:
        return resource_id in self._downloads_in_progress

    def has_failed(self, resource_id: int) -> bool:
        return resource_id in self._download_failed

    def mark_failed(self, resource_id: int) -> None:
        self._download_failed.add(resource_id)

    def clear_failed(self, resource_id: int) -> None:
        self._download_failed.discard(resource_id)

    # ------------------------------------------------------------------ #
    # Indirme
    # ------------------------------------------------------------------ #

    def start_download(self, resource: Resource) -> None:
        if resource.id in self._downloads_in_progress or not resource.url:
            return
        self._downloads_in_progress.add(resource.id)
        worker = PdfDownloadWorker(resource.id, resource.url, pdf_storage_dir())
        worker.signals.finished.connect(self._on_download_finished)
        self._ctx.thread_pool.start(worker)

    def _on_download_finished(self, resource_id: int, path: str | None) -> None:
        self._downloads_in_progress.discard(resource_id)
        self.downloadFinished.emit(resource_id, path)

    # ------------------------------------------------------------------ #
    # QPdfDocument onbellegi ve geometri
    # ------------------------------------------------------------------ #

    def load_document(self, file_url: str) -> QPdfDocument | None:
        cached = self._document_cache.get(file_url)
        if cached is not None:
            return cached
        local_path = QUrl(file_url).toLocalFile() or file_url
        doc = QPdfDocument()
        doc.load(local_path)
        if doc.status() != QPdfDocument.Status.Ready:
            return None
        self._document_cache[file_url] = doc
        return doc

    def select_text(self, file_url: str, selection: dict):
        """QML'in gonderdigi secim ({page, fromX, fromY, toX, toY}; page-point uzayinda) icin
        `(doc, page, QPdfSelection)` doner; belge/secim gecersizse ya da bossa None.

        QML'den `QPdfSelection` donen metotlar (getSelection/getSelectionAtIndex) cagrilamiyor --
        "Unknown method return type: QPdfSelection" (calisma zamaninda dogrulandi). Bu yuzden secim
        noktalari Python'a tasinip QPdfDocument islemleri burada yapiliyor.
        """
        doc = self.load_document(file_url)
        if doc is None:
            return None
        page = int(selection["page"])
        pdf_selection = doc.getSelection(
            page,
            QPointF(selection["fromX"], selection["fromY"]),
            QPointF(selection["toX"], selection["toY"]),
        )
        if not pdf_selection.isValid() or not sanitize_utf8(pdf_selection.text()).strip():
            return None
        return doc, page, pdf_selection

    @staticmethod
    def highlight_geometry(
        doc: QPdfDocument, page: int, start_index: int, length: int
    ) -> tuple[list, list] | None:
        selection = doc.getSelectionAtIndex(page, start_index, length)
        if not selection.isValid():
            return None
        polygons = [[[point.x(), point.y()] for point in polygon] for polygon in selection.bounds()]
        rect = selection.boundingRectangle()
        return polygons, [rect.x(), rect.y(), rect.width(), rect.height()]

    # ------------------------------------------------------------------ #
    # Temizlik
    # ------------------------------------------------------------------ #

    def cleanup_local_pdf(self, url: str) -> None:
        """Kaynak silinince ilgili QPdfDocument onbellek girdisini ve --
        sadece bizim kopyaladigimiz (pdf_storage_dir icindeki) dosyayi --
        diskten temizler. Kullanicinin kendi dosyalarina asla dokunmaz."""
        self.documentReleased.emit(url)
        cached_doc = self._document_cache.pop(url, None)
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
