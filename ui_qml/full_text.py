from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from workers import ExtractWorker

if TYPE_CHECKING:
    from ui_qml.context import BridgeContext

STATE_PENDING = "pending"  # cikarim suruyor
STATE_FAILED = "failed"  # cikarim bitti, metin yok (site robotlara kapali, icerik yok, ag hatasi...)


class FullTextExtractor(QObject):
    """Kaynagin tam metnini arka planda cikarip kaydeder (Library, Reader ve Market ortak kullanir).

    `extracted(resource_id, full_text)` kaynak guncellendikten SONRA yayilir; acik okuyucu buna gore kendini tazeler.
    `statusChanged(resource_id)` cikarim baslayinca/basarisiz bitince yayilir (okuyucu "cekiliyor" ile "bulunamadi"yi
    ayirabilsin); `pdfDetected(resource_id)` URL bir web sayfasi sanilirken aslinda PDF dosyasi cikinca yayilir."""

    extracted = Signal(int, str)
    statusChanged = Signal(int)
    pdfDetected = Signal(int)

    def __init__(self, ctx: "BridgeContext", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._pending: set[int] = set()
        self._failed: set[int] = set()

    def state(self, resource_id: int) -> str:
        """'pending' | 'failed' | '' (hic denenmedi ya da basarili)."""
        if resource_id in self._pending:
            return STATE_PENDING
        return STATE_FAILED if resource_id in self._failed else ""

    def schedule(self, resource_id: int, url: str) -> None:
        worker = ExtractWorker(resource_id, url)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.pdfDetected.connect(self.pdfDetected)
        self._pending.add(resource_id)
        self._failed.discard(resource_id)
        self.statusChanged.emit(resource_id)
        self._ctx.thread_pool.start(worker)

    def _on_finished(self, resource_id: int, full_text: str | None) -> None:
        self._pending.discard(resource_id)
        if not full_text:
            self._failed.add(resource_id)
            self.statusChanged.emit(resource_id)
            return
        self._failed.discard(resource_id)
        changes: dict = {"full_text": full_text}
        if full_text.startswith("<h3>Sayfa "):  # PDF'ten uretildi: paragraf bicimi surum 2 (eski metin yeniden olusturulabilsin)
            resource = self._ctx.controllers.resources.get_resource(resource_id)
            if resource is not None:
                changes["extra_metadata"] = {**(resource.extra_metadata or {}), "reflow": 2}
        self._ctx.controllers.resources.update_resource(resource_id, changes)
        self.extracted.emit(resource_id, full_text)
        self.statusChanged.emit(resource_id)
