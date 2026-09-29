from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log
from services.paper_market_service import PaperMarketService


class RelatedPapersWorkerSignals(QObject):
    # openalex_id, kind ("references" | "citations"), list[PaperResult], hata mesaji ("" = hata yok)
    finished = Signal(str, str, object, str)


class RelatedPapersWorker(QRunnable):
    """Bir makalenin referanslarini ya da ona atif yapan eserleri OpenAlex'ten getirir."""

    def __init__(self, openalex_id: str, kind: str) -> None:
        super().__init__()
        self._openalex_id = openalex_id
        self._kind = kind
        self.signals = RelatedPapersWorkerSignals()

    def run(self) -> None:
        papers, error = [], ""
        try:
            papers = PaperMarketService().related_papers(self._openalex_id, self._kind)
        except Exception as exc:
            log.exception("Iliskili makaleler getirilemedi: %s %s", self._openalex_id, self._kind)
            error = str(exc) or exc.__class__.__name__
        self.signals.finished.emit(self._openalex_id, self._kind, papers, error)
