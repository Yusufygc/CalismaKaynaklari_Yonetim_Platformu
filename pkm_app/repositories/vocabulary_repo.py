from sqlalchemy.orm import Session, joinedload

from models import Vocabulary
from .base_repository import BaseRepository


class VocabularyRepository(BaseRepository[Vocabulary]):

    def __init__(self, session: Session) -> None:
        super().__init__(Vocabulary, session)

    def get_by_resource(self, resource_id: int) -> list[Vocabulary]:
        return (
            self._session.query(Vocabulary)
            .filter(Vocabulary.resource_id == resource_id)
            .order_by(Vocabulary.created_at.desc(), Vocabulary.id.desc())
            .all()
        )

    def get_all_with_resource(self) -> list[Vocabulary]:
        """Bilgi Havuzu icin kaynak basligini da eager-load eder (N+1 onler)."""
        return (
            self._session.query(Vocabulary)
            .options(joinedload(Vocabulary.resource))
            .order_by(Vocabulary.created_at.desc(), Vocabulary.id.desc())
            .all()
        )
