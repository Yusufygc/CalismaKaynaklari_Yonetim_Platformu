from sqlalchemy.orm import Session

from core.events import event_bus
from core.logger import log
from services.tag_service import TagService


class TagController:
    """Etiket islemleri icin UI sinirindaki hata yakalama/sinyal katmani."""

    def __init__(self, session: Session) -> None:
        self._svc = TagService(session)

    def load_tags(self) -> list:
        return self._svc.get_all()

    def create_tag(self, name: str) -> object:
        try:
            tag = self._svc.create_tag(name)
            event_bus.tag_added.emit(tag.id)
            return tag
        except Exception as exc:
            log.exception("Etiket eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def update_tag(self, tag_id: int, new_name: str) -> object:
        try:
            tag = self._svc.update_tag(tag_id, new_name)
            event_bus.tag_updated.emit(tag.id)
            return tag
        except Exception as exc:
            log.exception("Etiket guncellenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def delete_tag(self, tag_id: int) -> bool:
        try:
            self._svc.delete_tag(tag_id)
            event_bus.tag_deleted.emit(tag_id)
            return True
        except Exception as exc:
            log.exception("Etiket silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False
