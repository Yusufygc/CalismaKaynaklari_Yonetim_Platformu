from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from workers import ExtractWorker

if TYPE_CHECKING:
    from ui_qml.context import BridgeContext


class FullTextExtractor(QObject):
    """Kaynagin tam metnini arka planda cikarip kaydeder (Library, Reader ve Market ortak kullanir).

    `extracted(resource_id, full_text)` kaynak guncellendikten SONRA yayilir; acik okuyucu buna
    gore kendini tazeler."""

    extracted = Signal(int, str)

    def __init__(self, ctx: "BridgeContext", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx

    def schedule(self, resource_id: int, url: str) -> None:
        worker = ExtractWorker(resource_id, url)
        worker.signals.finished.connect(self._on_finished)
        self._ctx.thread_pool.start(worker)

    def _on_finished(self, resource_id: int, full_text: str | None) -> None:
        if not full_text:
            return
        self._ctx.controllers.resources.update_resource(resource_id, {"full_text": full_text})
        self.extracted.emit(resource_id, full_text)
