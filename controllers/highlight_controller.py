from sqlalchemy.orm import Session

from core.events import event_bus
from core.logger import log
from services.highlight_service import HighlightService


class HighlightController:
    """Alinti (Highlight) islemleri icin UI sinirindaki hata yakalama/sinyal katmani."""

    def __init__(self, session: Session) -> None:
        self._svc = HighlightService(session)

    def create_highlight(self, resource_id: int, content: str, color: str | None = None) -> object:
        try:
            highlight = self._svc.create_highlight(resource_id, content, color)
            event_bus.highlight_added.emit(highlight.id)
            return highlight
        except Exception as exc:
            log.error("Alinti eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def delete_highlight(self, highlight_id: int) -> bool:
        try:
            self._svc.delete_highlight(highlight_id)
            event_bus.highlight_deleted.emit(highlight_id)
            return True
        except Exception as exc:
            log.error("Alinti silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False

    def load_resource_highlights(self, resource_id: int) -> list:
        return self._svc.get_by_resource(resource_id)

    def load_all_highlights(self) -> list:
        return self._svc.get_all()
