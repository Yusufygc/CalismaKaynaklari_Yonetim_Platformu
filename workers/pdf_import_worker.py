import shutil
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log


class PdfImportWorkerSignals(QObject):
    finished = Signal(str, str, str)  # kaynak yolu, hedef yolu, hata mesaji ("" = hata yok)


class PdfImportWorker(QRunnable):
    """Yerel bir PDF'i depoya kopyalar (buyuk dosyalarda UI thread'i donmasin). Orijinale dokunmaz."""

    def __init__(self, source: Path, destination: Path) -> None:
        super().__init__()
        self._source = source
        self._destination = destination
        self.signals = PdfImportWorkerSignals()

    def run(self) -> None:
        error = ""
        try:
            shutil.copyfile(self._source, self._destination)
        except OSError as exc:
            log.warning("PDF kopyalanamadi: %s - %s", self._source, exc)
            error = str(exc) or exc.__class__.__name__
        self.signals.finished.emit(str(self._source), str(self._destination), error)
