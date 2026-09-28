from sqlalchemy.orm import Session

from core.exceptions import ResourceNotFoundError, ValidationError
from core.logger import log
from models import PdfNote
from repositories.pdf_note_repo import PdfNoteRepository
from repositories.resource_repo import ResourceRepository


class PdfNoteService:

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = PdfNoteRepository(session)
        self._resource_repo = ResourceRepository(session)

    def create_note(self, resource_id: int, page: int, x: float, y: float, note_text: str) -> PdfNote:
        note_text = (note_text or "").strip()
        if not note_text:
            raise ValidationError("Not metni bos olamaz.")
        if self._resource_repo.get_by_id(resource_id) is None:
            raise ResourceNotFoundError(f"Kaynak bulunamadi: id={resource_id}")
        try:
            note = PdfNote(resource_id=resource_id, page=page, x=x, y=y, note_text=note_text)
            self._repo.create(note)
            self._session.commit()
            log.info("Yeni PDF notu eklendi: resource_id=%d", resource_id)
            return note
        except Exception:
            self._session.rollback()
            log.exception("PDF notu eklenirken hata olustu.")
            raise

    def update_note(self, note_id: int, note_text: str) -> PdfNote:
        note_text = (note_text or "").strip()
        if not note_text:
            raise ValidationError("Not metni bos olamaz.")
        note = self._repo.get_by_id(note_id)
        if note is None:
            raise ResourceNotFoundError(f"Not bulunamadi: id={note_id}")
        try:
            note.note_text = note_text
            self._repo.update(note)
            self._session.commit()
            log.info("PDF notu guncellendi: id=%d", note_id)
            return note
        except Exception:
            self._session.rollback()
            log.exception("PDF notu guncellenirken hata olustu.")
            raise

    def get_by_resource(self, resource_id: int) -> list[PdfNote]:
        return self._repo.get_by_resource(resource_id)

    def delete_note(self, note_id: int) -> None:
        try:
            deleted = self._repo.delete(note_id)
            if not deleted:
                raise ResourceNotFoundError(f"Not bulunamadi: id={note_id}")
            self._session.commit()
            log.info("PDF notu silindi: id=%d", note_id)
        except Exception:
            self._session.rollback()
            log.exception("PDF notu silinirken hata olustu.")
            raise
