from PySide6.QtCore import QObject, QRunnable, Signal

from core.logger import log
from services.reading_suggestion_service import ReadingSuggestionService


class ReadingSuggestionWorkerSignals(QObject):
    # list[Suggestion], hata mesaji ("" = hata yok)
    finished = Signal(object, str)


class ReadingSuggestionWorker(QRunnable):
    """Kutuphanedeki makalelerin ortak referanslarindan okuma onerisi uretir (ag isi)."""

    def __init__(self, library_openalex_ids: list[str]) -> None:
        super().__init__()
        self._ids = library_openalex_ids
        self.signals = ReadingSuggestionWorkerSignals()

    def run(self) -> None:
        suggestions, error = [], ""
        try:
            suggestions = ReadingSuggestionService().suggest(self._ids)
        except Exception as exc:
            log.exception("Okuma onerileri getirilemedi: %d kaynak", len(self._ids))
            error = str(exc) or exc.__class__.__name__
        self.signals.finished.emit(suggestions, error)
