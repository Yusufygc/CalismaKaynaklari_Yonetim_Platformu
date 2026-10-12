from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from core.logger import log


class _Signals(QObject):
    done = Signal(object, object, object)  # geri cagri, sonuc, hata (Exception | None)


class CallWorker(QRunnable):
    """`fn`'i havuz thread'inde calistirir; sonucu/hatayi `dispatch` (ana thread'deki bir QObject metodu)
    uzerinden `callback(sonuc, hata)` olarak teslim eder."""

    def __init__(self, fn: Callable[[], Any], callback: Callable[[Any, Exception | None], None]) -> None:
        super().__init__()
        self._fn = fn
        self._callback = callback
        self.signals = _Signals()

    def run(self) -> None:
        result, error = None, None
        try:
            result = self._fn()
        except Exception as exc:  # worker disina tasmasin; hata callback'e gider
            log.warning("pdfkit arka plan isi basarisiz: %s: %s", exc.__class__.__name__, exc)
            error = exc
        self.signals.done.emit(self._callback, result, error)


def submit(pool: QThreadPool, worker: CallWorker, dispatch: Callable[[Any, Any, Any], None]) -> None:
    """`dispatch` bir QObject'in bagli metodu olmali (kuyruklu baglanti ile ana thread'e teslim)."""
    worker.signals.done.connect(dispatch)
    pool.start(worker)
