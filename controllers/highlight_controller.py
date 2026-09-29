from sqlalchemy.orm import Session

from core.events import event_bus
from core.logger import log
from services.highlight_service import HighlightService
from services.schemas import HighlightPosition


class HighlightController:
    """Alinti (Highlight) islemleri icin UI sinirindaki hata yakalama/sinyal katmani."""

    def __init__(self, session: Session) -> None:
        self._svc = HighlightService(session)

    def create_highlight(
        self,
        resource_id: int,
        content: str,
        color: str | None = None,
        position: HighlightPosition | None = None,
    ) -> object:
        try:
            highlight = self._svc.create_highlight(resource_id, content, color, position)
            event_bus.highlight_added.emit(highlight.id)
            return highlight
        except Exception as exc:
            log.exception("Alinti eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def update_highlight_color(self, highlight_id: int, color: str) -> object:
        try:
            highlight = self._svc.update_highlight_color(highlight_id, color)
            event_bus.highlight_updated.emit(highlight_id)
            return highlight
        except Exception as exc:
            log.exception("Alinti rengi guncellenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def update_highlight_comment(self, highlight_id: int, comment: str) -> object:
        try:
            highlight = self._svc.update_highlight_comment(highlight_id, comment)
            event_bus.highlight_updated.emit(highlight_id)
            return highlight
        except Exception as exc:
            log.exception("Alinti yorumu guncellenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def delete_highlight(self, highlight_id: int) -> bool:
        try:
            self._svc.delete_highlight(highlight_id)
            event_bus.highlight_deleted.emit(highlight_id)
            return True
        except Exception as exc:
            log.exception("Alinti silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False

    def delete_highlights(self, highlight_ids: list[int]) -> int | None:
        """Silinen alinti sayisi; hata olursa None (hata event_bus ile bildirilir)."""
        try:
            deleted = self._svc.delete_highlights(highlight_ids)
            if deleted:
                event_bus.highlight_deleted.emit(0)  # Tek sinyal: dinleyenler bir kez yenilenir.
            return deleted
        except Exception as exc:
            log.exception("Alintilar toplu silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def load_resource_highlights(self, resource_id: int) -> list:
        return self._svc.get_by_resource(resource_id)

    def load_all_highlights(self) -> list:
        return self._svc.get_all()
