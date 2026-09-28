from sqlalchemy.orm import Session

from models import Resource
from controllers.category_controller import CategoryController
from controllers.highlight_controller import HighlightController
from controllers.resource_controller import ResourceController
from controllers.tag_controller import TagController
from controllers.vocabulary_controller import VocabularyController


class MainController:
    """Kaynak/Kategori/Etiket/Alinti/Kelime alt-controller'larini birlestiren ince facade.

    Tum is mantigi ve UI sinirindaki hata yakalama/sinyal firlatma ilgili
    alt-controller'da yasar (bkz. resource_controller.py, category_controller.py,
    tag_controller.py, highlight_controller.py, vocabulary_controller.py) --
    burasi sadece tek bir DI noktasi (views/flow'lar tek bir `controller`
    nesnesi enjekte eder) korumak icin delege eder.
    """

    def __init__(self, session: Session) -> None:
        self._resource = ResourceController(session)
        self._category = CategoryController(session)
        self._tag = TagController(session)
        self._highlight = HighlightController(session)
        self._vocabulary = VocabularyController(session)

    # ------------------------------------------------------------------ #
    # Kaynak islemleri
    # ------------------------------------------------------------------ #

    def load_resources_with_filters(self, filters: dict) -> list[Resource]:
        return self._resource.load_resources_with_filters(filters)

    def get_resource(self, resource_id: int) -> Resource | None:
        return self._resource.get_resource(resource_id)

    def add_resource(self, data: dict) -> Resource | None:
        return self._resource.add_resource(data)

    def update_resource(self, resource_id: int, data: dict) -> Resource | None:
        return self._resource.update_resource(resource_id, data)

    def toggle_pin(self, resource_id: int) -> None:
        self._resource.toggle_pin(resource_id)

    def toggle_favorite(self, resource_id: int) -> None:
        self._resource.toggle_favorite(resource_id)

    def delete_resource(self, resource_id: int) -> None:
        self._resource.delete_resource(resource_id)

    # ------------------------------------------------------------------ #
    # Kategori / Etiket
    # ------------------------------------------------------------------ #

    def load_categories(self) -> list:
        return self._category.load_categories()

    def load_tags(self) -> list:
        return self._tag.load_tags()

    def create_category(self, name: str, color_hex: str, icon: str = "") -> object:
        return self._category.create_category(name, color_hex, icon)

    def update_category(self, category_id: int, name: str,
                        color_hex: str, icon: str = "") -> object:
        return self._category.update_category(category_id, name, color_hex, icon)

    def delete_category(self, category_id: int) -> bool:
        return self._category.delete_category(category_id)

    def create_tag(self, name: str) -> object:
        return self._tag.create_tag(name)

    def update_tag(self, tag_id: int, new_name: str) -> object:
        return self._tag.update_tag(tag_id, new_name)

    def delete_tag(self, tag_id: int) -> bool:
        return self._tag.delete_tag(tag_id)

    # ------------------------------------------------------------------ #
    # Alinti (Highlight) / Kelime (Vocabulary)
    # ------------------------------------------------------------------ #

    def create_highlight(self, resource_id: int, content: str, color: str | None = None) -> object:
        return self._highlight.create_highlight(resource_id, content, color)

    def delete_highlight(self, highlight_id: int) -> bool:
        return self._highlight.delete_highlight(highlight_id)

    def load_resource_highlights(self, resource_id: int) -> list:
        return self._highlight.load_resource_highlights(resource_id)

    def load_all_highlights(self) -> list:
        return self._highlight.load_all_highlights()

    def create_vocabulary(
        self, resource_id: int, word: str, translation: str, context_sentence: str | None = None
    ) -> object:
        return self._vocabulary.create_vocabulary(resource_id, word, translation, context_sentence)

    def delete_vocabulary(self, vocabulary_id: int) -> bool:
        return self._vocabulary.delete_vocabulary(vocabulary_id)

    def load_resource_vocabulary(self, resource_id: int) -> list:
        return self._vocabulary.load_resource_vocabulary(resource_id)

    def load_all_vocabulary(self) -> list:
        return self._vocabulary.load_all_vocabulary()
