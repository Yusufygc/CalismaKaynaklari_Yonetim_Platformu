from sqlalchemy.orm import Session

from models import Tag
from .base_repository import BaseRepository


class TagRepository(BaseRepository[Tag]):

    def __init__(self, session: Session) -> None:
        super().__init__(Tag, session)

    def get_by_name(self, name: str) -> Tag | None:
        return (
            self._session.query(Tag)
            .filter(Tag.name == name.lower().strip())
            .first()
        )
