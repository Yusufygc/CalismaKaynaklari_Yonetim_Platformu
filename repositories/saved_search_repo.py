from sqlalchemy.orm import Session

from models import SavedSearch
from .base_repository import BaseRepository


class SavedSearchRepository(BaseRepository[SavedSearch]):

    def __init__(self, session: Session) -> None:
        super().__init__(SavedSearch, session)

    def get_all_ordered(self) -> list[SavedSearch]:
        return (
            self._session.query(SavedSearch)
            .order_by(SavedSearch.created_at.desc(), SavedSearch.id.desc())
            .all()
        )
