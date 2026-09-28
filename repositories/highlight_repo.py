from sqlalchemy.orm import Session, joinedload

from models import Highlight
from .base_repository import BaseRepository


class HighlightRepository(BaseRepository[Highlight]):

    def __init__(self, session: Session) -> None:
        super().__init__(Highlight, session)

    def get_by_resource(self, resource_id: int) -> list[Highlight]:
        return (
            self._session.query(Highlight)
            .filter(Highlight.resource_id == resource_id)
            .order_by(Highlight.created_at.desc(), Highlight.id.desc())
            .all()
        )

    def get_all_with_resource(self) -> list[Highlight]:
        """Bilgi Havuzu icin kaynak basligini da eager-load eder (N+1 onler)."""
        return (
            self._session.query(Highlight)
            .options(joinedload(Highlight.resource))
            .order_by(Highlight.created_at.desc(), Highlight.id.desc())
            .all()
        )
