from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log
from services.paper_market_service import PaperMarketService


class PaperMetadataWorkerSignals(QObject):
    # resource_id, PaperResult | None, hata mesaji ("" = hata yok; None sonuc + bos hata = bulunamadi)
    finished = Signal(int, object, str)


class PaperMetadataWorker(QRunnable):
    """Bir kaynagin akademik bilgilerini (yazar/yil/dergi/DOI/OpenAlex id) OpenAlex'ten getirir."""

    def __init__(self, resource_id: int, doi: str | None, title: str | None) -> None:
        super().__init__()
        self._resource_id = resource_id
        self._doi = doi
        self._title = title
        self.signals = PaperMetadataWorkerSignals()

    def run(self) -> None:
        paper, error = None, ""
        try:
            paper = PaperMarketService().find_paper_strict(doi=self._doi, title=self._title)
        except Exception as exc:
            log.exception("Makale bilgisi getirme worker'i basarisiz: id=%d", self._resource_id)
            error = str(exc) or exc.__class__.__name__
        self.signals.finished.emit(self._resource_id, paper, error)
