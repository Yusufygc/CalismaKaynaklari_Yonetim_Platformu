"""Yerel PDF dosyalari: URL cozumleme, web PDF indirme durumu, temizlik.

Reader (okuyucu), Library (kaynak silme/duzenleme) ve serilestirici ortak kullanir; bu yuzden
kopya/durum tek yerde tutulur. Kaynak guncelleme gibi is kurallari burada DEGIL, indirme
sonucunu isleyen `ReaderBridge`'dedir.
"""
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, QUrl, Signal

from core.logger import log
from core.paths import pdf_storage_dir
from models import Resource

if TYPE_CHECKING:
    from ui_qml.context import BridgeContext


class PdfFileManager(QObject):
    downloadFinished = Signal(int, object)  # kaynak id, yerel dosya yolu (str) | None
    documentReleased = Signal(str)  # silinen kaynagin dosya URL'si (anahat onbellegi gibi turevler temizlensin)

    def __init__(self, ctx: "BridgeContext", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
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
        self._ctx.pdf_library.download_remote(resource.id, resource.url)

    def on_download_finished(self, resource_id: int, path: Path | None) -> None:
        """`PdfLibrary.downloadFinished` sonucu: depodaki dosya yolu ya da basarisizlik (None)."""
        self._downloads_in_progress.discard(resource_id)
        self.downloadFinished.emit(resource_id, str(path) if path else None)

    # ------------------------------------------------------------------ #
    # Temizlik
    # ------------------------------------------------------------------ #

    def cleanup_local_pdf(self, url: str) -> None:
        """Kaynak silinince okuyucu turevlerini temizler ve -- sadece bizim kopyaladigimiz (pdf_storage_dir
        icindeki) dosyayi -- diskten kaldirir. Kullanicinin kendi dosyalarina asla dokunmaz. Acik belgeyi
        pdfkit `DocumentSession` yonetir (kaynak silinirken kapanir)."""
        self.documentReleased.emit(url)
        if not (url.startswith("file://") and url.lower().endswith(".pdf")):
            return
        local_path = Path(QUrl(url).toLocalFile() or url)
        if self._ctx.pdf_library.owns(local_path):
            # Icerik adresli depo dosyasi baska kaynaklarla paylasiliyor olabilir: dogrudan silinmez, kimse
            # kullanmiyorsa cop toplama karantinaya alir (Windows kilidi icin yeniden denenir).
            self._ctx.pdf_library.collect_garbage(attempts=6)
        elif pdf_storage_dir() in local_path.resolve().parents:
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
