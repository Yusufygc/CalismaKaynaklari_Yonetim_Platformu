import threading
from collections import deque
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QThreadPool, QTimer, Signal

from core.logger import log
from pdfkit.app.search import MAX_INDEXED_PAGES
from pdfkit.domain.errors import PdfkitError
from pdfkit.infra.text import iter_page_texts
from pdfkit.ui.library import PdfLibrary
from pdfkit.ui.workers import CallWorker, submit

_WRITE_CHUNK = 10  # her olay dongusu turunda dizine yazilan sayfa sayisi (UI donmasin)

STATE_IDLE = "idle"
STATE_RUNNING = "running"
STATE_UNAVAILABLE = "unavailable"  # SQLite'ta FTS5 yok: arama kapali


def extract_pages(path: Path, cancelled: threading.Event) -> list[str] | None:
    """Worker thread'inde: sayfa metinlerini okur. Sayfalar arasinda iptal denetlenir; iptalde None."""
    pages: list[str] = []
    reader = iter_page_texts(path, MAX_INDEXED_PAGES)
    try:
        for text in reader:
            if cancelled.is_set():
                return None
            pages.append(text)
    finally:
        reader.close()
    return pages


class TextIndexer(QObject):
    """Belgelerin sayfa metnini arka planda tam metin dizinine alir (K8/K9): metin cikarimi havuz thread'inde (iptal
    edilebilir), veritabani yazimi ana thread'de kucuk dilimlerle. Bir seferde tek belge; kuyruk sirayla islenir.

    Yarim kalan dizin (iptal, cokme) aranmaz: durum `indexing` kalir ve sonraki taramada belge bastan dizinlenir."""

    statusChanged = Signal()
    finished = Signal()  # kuyruk bosaldi

    def __init__(
        self,
        library: PdfLibrary,
        thread_pool: Callable[[], QThreadPool],
        write_chunk: int = _WRITE_CHUNK,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._library = library
        self._thread_pool = thread_pool
        self._write_chunk = write_chunk
        self._queue: deque[int] = deque()
        self._current: int | None = None
        self._pages: list[str] = []
        self._written = 0
        self._total = 0
        self._done = 0
        self._cancelled = threading.Event()
        self._unavailable = False
        self._checked = False

    # ------------------------------------------------------------------ #
    # Disariya acik
    # ------------------------------------------------------------------ #

    def status(self) -> dict:
        state = STATE_UNAVAILABLE if self._unavailable else (STATE_RUNNING if self._current is not None else STATE_IDLE)
        return {"state": state, "done": self._done, "total": self._total, "pending": len(self._queue) + (self._current is not None)}

    def scan(self) -> None:
        """Dizinlenmesi gereken tum belgeleri kuyruga alir (acilista, eski/yarim dizinler icin) ve yetim satirlari temizler."""
        if not self._usable():
            return
        service = self._library.indexing()
        try:
            service.purge_orphans()
        except Exception:
            log.warning("Yetim dizin satirlari temizlenemedi.", exc_info=True)
        for document_id in service.pending():
            self.enqueue(document_id)

    def _usable(self) -> bool:
        """Dizin tablosu var mi (ilk kullanimda denetlenir; FTS5 yoksa indeksleyici kapali kalir)."""
        if not self._checked:
            self._checked = True
            self._unavailable = not self._library.indexing().available()
            if self._unavailable:
                self.statusChanged.emit()
        return not self._unavailable

    def enqueue(self, document_id: int) -> None:
        if document_id == self._current or document_id in self._queue or not self._usable():
            return
        if self._current is None and not self._queue:
            self._total = self._done = 0  # yeni bir tur basliyor
        self._queue.append(document_id)
        self._total += 1
        self.statusChanged.emit()
        if self._current is None:
            QTimer.singleShot(0, self._start_next)

    def cancel(self) -> None:
        """Kuyrugu bosaltir ve calisan isi sayfalar arasinda durdurur (yarim dizin silinir)."""
        self._queue.clear()
        self._cancelled.set()

    # ------------------------------------------------------------------ #
    # Isleyis
    # ------------------------------------------------------------------ #

    def _start_next(self) -> None:
        if self._current is not None:
            return
        if not self._queue:
            self._cancelled.clear()
            self.statusChanged.emit()
            self.finished.emit()
            return
        document_id = self._queue.popleft()
        self._current = document_id
        self._cancelled.clear()
        try:
            document = self._library.documents().get(document_id)
            if document is None:
                raise PdfkitError("Belge yok")
            path = self._library.file_path(document)
            if not path.is_file():
                raise PdfkitError("Belge dosyasi yok")
            self._library.indexing().begin(document_id)
        except Exception as exc:
            log.warning("Belge dizinlenemedi (id=%d): %s", document_id, exc)
            self._step_done(document_id, "fail")
            return
        cancelled = self._cancelled
        submit(
            self._thread_pool(),
            CallWorker(lambda: extract_pages(path, cancelled), self._on_extracted),
            self._dispatch,
        )
        self.statusChanged.emit()

    def _dispatch(self, callback, result, error) -> None:
        callback(result, error)

    def _on_extracted(self, pages: list[str] | None, error: Exception | None) -> None:
        document_id = self._current
        if document_id is None:
            return
        if error is not None:
            self._step_done(document_id, "fail")
        elif pages is None or self._cancelled.is_set():
            self._step_done(document_id, "abandon")
        elif not any(page.strip() for page in pages):
            self._step_done(document_id, "no_text", len(pages))
        else:
            self._pages, self._written = pages, 0
            QTimer.singleShot(0, self._write_next)

    def _write_next(self) -> None:
        document_id = self._current
        if document_id is None:
            return
        if self._cancelled.is_set():
            self._step_done(document_id, "abandon")
            return
        end = min(self._written + self._write_chunk, len(self._pages))
        try:
            self._library.indexing().add_pages(document_id, self._written, self._pages[self._written:end])
        except Exception as exc:  # ornegin belge arada silindi
            log.warning("Dizine yazilamadi (id=%d): %s", document_id, exc)
            self._step_done(document_id, "abandon")
            return
        self._written = end
        if end < len(self._pages):
            QTimer.singleShot(0, self._write_next)
        else:
            self._step_done(document_id, "ok", len(self._pages))

    def _step_done(self, document_id: int, outcome: str, page_count: int = 0) -> None:
        service = self._library.indexing()
        try:
            if outcome == "ok":
                service.finish(document_id, page_count)
            elif outcome == "no_text":
                service.finish_without_text(document_id)
            elif outcome == "fail":
                service.fail(document_id)
            else:
                service.abandon(document_id)
        except Exception:
            log.warning("Dizin durumu yazilamadi (id=%d, %s)", document_id, outcome, exc_info=True)
        self._pages = []
        self._current = None
        self._done += 1
        self.statusChanged.emit()
        QTimer.singleShot(0, self._start_next)
