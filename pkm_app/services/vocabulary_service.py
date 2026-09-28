from sqlalchemy.orm import Session

from core.exceptions import ResourceNotFoundError, ValidationError
from core.logger import log
from models import Vocabulary
from repositories.resource_repo import ResourceRepository
from repositories.vocabulary_repo import VocabularyRepository


class VocabularyService:

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = VocabularyRepository(session)
        self._resource_repo = ResourceRepository(session)

    def create_vocabulary(
        self,
        resource_id: int,
        word: str,
        translation: str,
        context_sentence: str | None = None,
    ) -> Vocabulary:
        word = (word or "").strip()
        translation = (translation or "").strip()
        if not word:
            raise ValidationError("Kelime bos olamaz.")
        if not translation:
            raise ValidationError("Ceviri bos olamaz.")
        if self._resource_repo.get_by_id(resource_id) is None:
            raise ResourceNotFoundError(f"Kaynak bulunamadi: id={resource_id}")
        try:
            vocabulary = Vocabulary(
                resource_id=resource_id,
                word=word,
                translation=translation,
                context_sentence=context_sentence,
            )
            self._repo.create(vocabulary)
            self._session.commit()
            log.info("Yeni kelime eklendi: resource_id=%d word=%r", resource_id, word)
            return vocabulary
        except Exception:
            self._session.rollback()
            log.exception("Kelime eklenirken hata olustu.")
            raise

    def get_by_resource(self, resource_id: int) -> list[Vocabulary]:
        return self._repo.get_by_resource(resource_id)

    def get_all(self) -> list[Vocabulary]:
        return self._repo.get_all_with_resource()

    def delete_vocabulary(self, vocabulary_id: int) -> None:
        try:
            deleted = self._repo.delete(vocabulary_id)
            if not deleted:
                raise ResourceNotFoundError(f"Kelime bulunamadi: id={vocabulary_id}")
            self._session.commit()
            log.info("Kelime silindi: id=%d", vocabulary_id)
        except Exception:
            self._session.rollback()
            log.exception("Kelime silinirken hata olustu.")
            raise
