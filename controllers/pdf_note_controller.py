from sqlalchemy.orm import Session

from core.events import event_bus
from core.logger import log
from services.pdf_note_service import PdfNoteService


class PdfNoteController:
    """PDF notu islemleri icin UI sinirindaki hata yakalama/sinyal katmani."""

    def __init__(self, session: Session) -> None:
        self._svc = PdfNoteService(session)

    def create_note(self, resource_id: int, page: int, x: float, y: float, note_text: str) -> object:
        try:
            note = self._svc.create_note(resource_id, page, x, y, note_text)
            event_bus.pdf_note_added.emit(note.id)
            return note
        except Exception as exc:
            log.error("PDF notu eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def update_note(self, note_id: int, note_text: str) -> object:
        try:
            note = self._svc.update_note(note_id, note_text)
            event_bus.pdf_note_updated.emit(note_id)
            return note
        except Exception as exc:
            log.error("PDF notu guncellenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def delete_note(self, note_id: int) -> bool:
        try:
            self._svc.delete_note(note_id)
            event_bus.pdf_note_deleted.emit(note_id)
            return True
        except Exception as exc:
            log.error("PDF notu silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False

    def load_resource_notes(self, resource_id: int) -> list:
        return self._svc.get_by_resource(resource_id)
