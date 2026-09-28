from typing import Generic, TypeVar, Type
from sqlalchemy.orm import Session
from models import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Tüm modeller icin jenerik CRUD islemleri.

    Transaction yonetimi (commit/rollback) Service katmaninin
    sorumluluğundadir; bu sinif yalnizca sorgu hazirlar.
    """

    def __init__(self, model: Type[ModelT], session: Session) -> None:
        self._model = model
        self._session = session

    def get_by_id(self, record_id: int) -> ModelT | None:
        return self._session.get(self._model, record_id)

    def get_all(self) -> list[ModelT]:
        return list(self._session.query(self._model).all())

    def create(self, obj: ModelT) -> ModelT:
        self._session.add(obj)
        self._session.flush()  # ID'nin atanmasi icin flush; commit Service'te
        return obj

    def update(self, obj: ModelT) -> ModelT:
        self._session.add(obj)
        self._session.flush()
        return obj

    def delete(self, record_id: int) -> bool:
        obj = self.get_by_id(record_id)
        if obj is None:
            return False
        self._session.delete(obj)
        self._session.flush()
        return True
