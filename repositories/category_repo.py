from sqlalchemy.orm import Session

from models import Category
from .base_repository import BaseRepository


class CategoryRepository(BaseRepository[Category]):

    def __init__(self, session: Session) -> None:
        super().__init__(Category, session)

    def get_by_name(self, name: str) -> Category | None:
        return (
            self._session.query(Category)
            .filter(Category.name == name.strip())
            .first()
        )
