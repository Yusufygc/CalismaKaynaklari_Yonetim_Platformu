from sqlalchemy.orm import Session

from models import PdfNote
from .base_repository import BaseRepository


class PdfNoteRepository(BaseRepository[PdfNote]):

    def __init__(self, session: Session) -> None:
        super().__init__(PdfNote, session)

    def get_by_resource(self, resource_id: int) -> list[PdfNote]:
        return (
            self._session.query(PdfNote)
            .filter(PdfNote.resource_id == resource_id)
            .order_by(PdfNote.created_at.desc(), PdfNote.id.desc())
            .all()
        )
