from sqlalchemy.orm import Session

from core.events import event_bus
from core.logger import log
from models import Resource
from services.resource_service import ResourceService
from services.schemas import ResourceCreateSchema, ResourceUpdateSchema


class ResourceController:
    """Kaynak (Resource) islemleri icin UI sinirindaki hata yakalama/sinyal katmani."""

    def __init__(self, session: Session) -> None:
        self._svc = ResourceService(session)

    def load_resources_with_filters(self, filters: dict) -> list[Resource]:
        return self._svc.query_resources(filters)

    def get_resource(self, resource_id: int) -> Resource | None:
        try:
            return self._svc.get_by_id(resource_id)
        except Exception as exc:
            log.exception("Kaynak getirilemedi: id=%d", resource_id)
            event_bus.error_occurred.emit(str(exc))
            return None

    def add_resource(self, data: dict) -> Resource | None:
        try:
            payload = ResourceCreateSchema(**data)
            resource = self._svc.add_new_resource(payload)
            event_bus.resource_added.emit(resource.id)
            return resource
        except Exception as exc:
            log.exception("Kaynak eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def update_resource(self, resource_id: int, data: dict) -> Resource | None:
        try:
            payload = ResourceUpdateSchema(**data)
            resource = self._svc.update_resource(resource_id, payload)
            event_bus.resource_updated.emit(resource_id)
            return resource
        except Exception as exc:
            log.exception("[%s] Kaynak guncellenemedi: %s", exc.__class__.__name__, exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def toggle_pin(self, resource_id: int) -> bool:
        try:
            self._svc.toggle_pin(resource_id)
            event_bus.resource_updated.emit(resource_id)
            return True
        except Exception as exc:
            log.exception("Pin durumu degistirilemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False

    def toggle_favorite(self, resource_id: int) -> bool:
        try:
            self._svc.toggle_favorite(resource_id)
            event_bus.resource_updated.emit(resource_id)
            return True
        except Exception as exc:
            log.exception("Favori durumu degistirilemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False

    def delete_resource(self, resource_id: int) -> bool:
        try:
            self._svc.delete_resource(resource_id)
            event_bus.resource_deleted.emit(resource_id)
            return True
        except Exception as exc:
            log.exception("Kaynak silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False
