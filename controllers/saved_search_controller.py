from datetime import timedelta

from sqlalchemy.orm import Session

from core.events import event_bus
from core.logger import log
from services.saved_search_service import SavedSearchService


class SavedSearchController:
    """Kayitli arama islemleri icin UI sinirindaki hata yakalama/sinyal katmani."""

    def __init__(self, session: Session) -> None:
        self._svc = SavedSearchService(session)

    def load_saved_searches(self) -> list:
        return self._svc.list_all()

    def create_saved_search(
        self, topic: str, filters: dict | None, tag_name: str | None, seen_ids: list[str] | None
    ) -> object:
        try:
            search = self._svc.create(topic, filters, tag_name, seen_ids)
            event_bus.saved_search_changed.emit()
            return search
        except Exception as exc:
            log.exception("Arama kaydedilemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def delete_saved_search(self, search_id: int) -> bool:
        try:
            self._svc.delete(search_id)
            event_bus.saved_search_changed.emit()
            return True
        except Exception as exc:
            log.exception("Kayitli arama silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False

    def mark_saved_search_seen(self, search_id: int, ids: list[str]) -> object:
        try:
            search = self._svc.mark_seen(search_id, ids)
            event_bus.saved_search_changed.emit()
            return search
        except Exception as exc:
            log.exception("Kayitli arama guncellenemedi: %s", exc)
            return None  # Arka plan bakim islemi: kullaniciya hata gosterilmez.

    def record_saved_search_check(self, search_id: int, new_count: int) -> object:
        try:
            search = self._svc.record_check(search_id, new_count)
            event_bus.saved_search_changed.emit()
            return search
        except Exception as exc:
            log.exception("Kayitli arama kontrolu yazilamadi: %s", exc)
            return None  # Arka plan bakim islemi: kullaniciya hata gosterilmez.

    def load_due_saved_searches(self, max_age: timedelta) -> list:
        return self._svc.due_for_check(max_age)
