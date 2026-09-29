from sqlalchemy.orm import Session

from core.events import event_bus
from core.logger import log
from services.vocabulary_service import VocabularyService


class VocabularyController:
    """Kelime (Vocabulary) islemleri icin UI sinirindaki hata yakalama/sinyal katmani."""

    def __init__(self, session: Session) -> None:
        self._svc = VocabularyService(session)

    def create_vocabulary(
        self, resource_id: int, word: str, translation: str, context_sentence: str | None = None
    ) -> object:
        try:
            vocabulary = self._svc.create_vocabulary(
                resource_id, word, translation, context_sentence
            )
            event_bus.vocabulary_added.emit(vocabulary.id)
            return vocabulary
        except Exception as exc:
            log.exception("Kelime eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def delete_vocabulary(self, vocabulary_id: int) -> bool:
        try:
            self._svc.delete_vocabulary(vocabulary_id)
            event_bus.vocabulary_deleted.emit(vocabulary_id)
            return True
        except Exception as exc:
            log.exception("Kelime silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False

    def load_resource_vocabulary(self, resource_id: int) -> list:
        return self._svc.get_by_resource(resource_id)

    def load_all_vocabulary(self) -> list:
        return self._svc.get_all()
