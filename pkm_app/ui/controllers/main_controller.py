from sqlalchemy.orm import Session

from core.events import event_bus
from core.logger import log
from models import Resource
from services.category_service import CategoryService
from services.highlight_service import HighlightService
from services.resource_service import ResourceService
from services.tag_service import TagService
from services.vocabulary_service import VocabularyService
from services.schemas import ResourceCreateSchema, ResourceUpdateSchema


class MainController:
    """Arayüz olaylarini yakalar, Service katmanini cagirir, Event Bus'a sinyal fırlatir."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._resource_svc = ResourceService(session)
        self._category_svc = CategoryService(session)
        self._tag_svc = TagService(session)
        self._highlight_svc = HighlightService(session)
        self._vocabulary_svc = VocabularyService(session)

        self._connect_events()

    def _connect_events(self) -> None:
        pass

    # ------------------------------------------------------------------ #
    # Kaynak islemleri
    # ------------------------------------------------------------------ #

    def load_resources_with_filters(self, filters: dict) -> list[Resource]:
        return self._resource_svc.query_resources(filters)

    def get_resource(self, resource_id: int) -> Resource | None:
        try:
            return self._resource_svc.get_by_id(resource_id)
        except Exception:
            log.exception("Kaynak getirilemedi: id=%d", resource_id)
            return None

    def add_resource(self, data: dict) -> Resource | None:
        try:
            payload = ResourceCreateSchema(**data)
            resource = self._resource_svc.add_new_resource(payload)
            event_bus.resource_added.emit(resource.id)
            return resource
        except Exception as exc:
            log.error("Kaynak eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def update_resource(self, resource_id: int, data: dict) -> Resource | None:
        try:
            payload = ResourceUpdateSchema(**data)
            resource = self._resource_svc.update_resource(resource_id, payload)
            event_bus.resource_updated.emit(resource_id)
            return resource
        except Exception as exc:
            log.error("[%s] Kaynak guncellenemedi: %s", exc.__class__.__name__, exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def toggle_pin(self, resource_id: int) -> None:
        try:
            self._resource_svc.toggle_pin(resource_id)
            event_bus.resource_updated.emit(resource_id)
        except Exception as exc:
            log.error("Pin durumu degistirilemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))

    def toggle_favorite(self, resource_id: int) -> None:
        try:
            self._resource_svc.toggle_favorite(resource_id)
            event_bus.resource_updated.emit(resource_id)
        except Exception as exc:
            log.error("Favori durumu degistirilemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))

    def delete_resource(self, resource_id: int) -> None:
        try:
            self._resource_svc.delete_resource(resource_id)
            event_bus.resource_deleted.emit(resource_id)
        except Exception as exc:
            log.error("Kaynak silinemedi: %s", exc)

    # ------------------------------------------------------------------ #
    # Kategori / Etiket
    # ------------------------------------------------------------------ #

    def load_categories(self) -> list:
        return self._category_svc.get_all()

    def load_tags(self) -> list:
        return self._tag_svc.get_all()

    def create_category(self, name: str, color_hex: str, icon: str = "") -> object:
        try:
            cat = self._category_svc.create_category(name, color_hex, icon)
            event_bus.category_added.emit(cat.id)
            return cat
        except Exception as exc:
            log.error("Kategori eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def update_category(self, category_id: int, name: str,
                        color_hex: str, icon: str = "") -> object:
        try:
            cat = self._category_svc.update_category(category_id, name, color_hex, icon)
            event_bus.category_updated.emit(cat.id)
            return cat
        except Exception as exc:
            log.error("Kategori guncellenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def delete_category(self, category_id: int) -> bool:
        try:
            self._category_svc.delete_category(category_id)
            event_bus.category_deleted.emit(category_id)
            return True
        except Exception as exc:
            log.error("Kategori silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False

    def create_tag(self, name: str) -> object:
        try:
            tag = self._tag_svc.create_tag(name)
            event_bus.tag_added.emit(tag.id)
            return tag
        except Exception as exc:
            log.error("Etiket eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def update_tag(self, tag_id: int, new_name: str) -> object:
        try:
            tag = self._tag_svc.update_tag(tag_id, new_name)
            event_bus.tag_updated.emit(tag.id)
            return tag
        except Exception as exc:
            log.error("Etiket guncellenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def delete_tag(self, tag_id: int) -> bool:
        try:
            self._tag_svc.delete_tag(tag_id)
            event_bus.tag_deleted.emit(tag_id)
            return True
        except Exception as exc:
            log.error("Etiket silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False

    # ------------------------------------------------------------------ #
    # Alinti (Highlight) / Kelime (Vocabulary)
    # ------------------------------------------------------------------ #

    def create_highlight(self, resource_id: int, content: str, color: str | None = None) -> object:
        try:
            highlight = self._highlight_svc.create_highlight(resource_id, content, color)
            event_bus.highlight_added.emit(highlight.id)
            return highlight
        except Exception as exc:
            log.error("Alinti eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def delete_highlight(self, highlight_id: int) -> bool:
        try:
            self._highlight_svc.delete_highlight(highlight_id)
            event_bus.highlight_deleted.emit(highlight_id)
            return True
        except Exception as exc:
            log.error("Alinti silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False

    def load_resource_highlights(self, resource_id: int) -> list:
        return self._highlight_svc.get_by_resource(resource_id)

    def load_all_highlights(self) -> list:
        return self._highlight_svc.get_all()

    def create_vocabulary(
        self, resource_id: int, word: str, translation: str, context_sentence: str | None = None
    ) -> object:
        try:
            vocabulary = self._vocabulary_svc.create_vocabulary(
                resource_id, word, translation, context_sentence
            )
            event_bus.vocabulary_added.emit(vocabulary.id)
            return vocabulary
        except Exception as exc:
            log.error("Kelime eklenemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return None

    def delete_vocabulary(self, vocabulary_id: int) -> bool:
        try:
            self._vocabulary_svc.delete_vocabulary(vocabulary_id)
            event_bus.vocabulary_deleted.emit(vocabulary_id)
            return True
        except Exception as exc:
            log.error("Kelime silinemedi: %s", exc)
            event_bus.error_occurred.emit(str(exc))
            return False

    def load_resource_vocabulary(self, resource_id: int) -> list:
        return self._vocabulary_svc.get_by_resource(resource_id)

    def load_all_vocabulary(self) -> list:
        return self._vocabulary_svc.get_all()

    # ------------------------------------------------------------------ #
    # Slot'lar
    # ------------------------------------------------------------------ #

