from sqlalchemy.orm import Session

from core.events import event_bus
from core.logger import log
from services.category_service import CategoryService


class CategoryController:
    """Kategori islemleri icin UI sinirindaki hata yakalama/sinyal katmani."""

    def __init__(self, session: Session) -> None:
        self._svc = CategoryService(session)

    def load_categories(self) -> list:
        return self._svc.get_all()

    def create_category(self, name: str, color_hex: str, icon: str = "") -> object:
        try:
            cat = self._svc.create_category(name, color_hex, icon)
            event_bus.category_added.emit(cat.id)
            return cat
        except Exception as exc:
            log.exception("Kategori eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def update_category(self, category_id: int, name: str,
                        color_hex: str, icon: str = "") -> object:
        try:
            cat = self._svc.update_category(category_id, name, color_hex, icon)
            event_bus.category_updated.emit(cat.id)
            return cat
        except Exception as exc:
            log.exception("Kategori guncellenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def delete_category(self, category_id: int) -> bool:
        try:
            self._svc.delete_category(category_id)
            event_bus.category_deleted.emit(category_id)
            return True
        except Exception as exc:
            log.exception("Kategori silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False
