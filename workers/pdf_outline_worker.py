from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from utils.pdf_outline import read_outline


class PdfOutlineWorkerSignals(QObject):
    finished = Signal(str, object)  # dosya URL'si, list[{title, level, page}]


class PdfOutlineWorker(QRunnable):
    """PDF anahatini (pypdf) arka planda okur: buyuk PDF'lerde UI thread'i bloklanmasin.
    `read_outline` hata yakalayip bos liste dondurdugu icin burada ek try/except gerekmez."""

    def __init__(self, file_url: str, path: Path) -> None:
        super().__init__()
        self._file_url = file_url
        self._path = path
        self.signals = PdfOutlineWorkerSignals()

    def run(self) -> None:
        outline = read_outline(self._path) if self._path.is_file() else []
        self.signals.finished.emit(self._file_url, outline)
