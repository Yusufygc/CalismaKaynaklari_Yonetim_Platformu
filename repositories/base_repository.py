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

    def get_many(self, record_ids: list[int]) -> dict[int, ModelT]:
        """Kimlik -> kayit (tek sorgu; bulunmayanlar yok). Oturum kimlik haritasindaki kayitlar da sorguyla tazelenir."""
        ids = list(dict.fromkeys(record_ids))
        found: dict[int, ModelT] = {}
        for start in range(0, len(ids), 500):  # SQLite degisken sinirina takilmamak icin parcali
            chunk = ids[start:start + 500]
            for record in self._session.query(self._model).filter(self._model.id.in_(chunk)):
                found[record.id] = record
        return found

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
