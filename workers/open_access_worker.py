from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log
from services.open_access_service import OpenAccessService


class OpenAccessWorkerSignals(QObject):
    finished = Signal(int, object)  # resource_id, str | None (PDF adresi)


class OpenAccessWorker(QRunnable):
    """DOI'nin (yoksa basligin) acik erisimli PDF adresini arka plan thread'inde arar (UI thread'i bloklamaz)."""

    def __init__(self, resource_id: int, doi: str, title: str = "") -> None:
        super().__init__()
        self._resource_id = resource_id
        self._doi = doi
        self._title = title
        self.signals = OpenAccessWorkerSignals()

    def run(self) -> None:
        try:
            url = OpenAccessService().find_pdf_url(self._doi, self._title)
        except Exception:
            log.exception("Acik erisim aramasi basarisiz: id=%d", self._resource_id)
            url = None
        self.signals.finished.emit(self._resource_id, url)
