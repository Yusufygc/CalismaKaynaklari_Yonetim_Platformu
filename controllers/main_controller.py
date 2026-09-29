from sqlalchemy.orm import Session

from models import Resource
from controllers.category_controller import CategoryController
from controllers.highlight_controller import HighlightController
from controllers.pdf_note_controller import PdfNoteController
from controllers.resource_controller import ResourceController
from controllers.saved_search_controller import SavedSearchController
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
        self._pdf_note = PdfNoteController(session)
        self._saved_search = SavedSearchController(session)

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

    def toggle_pin(self, resource_id: int) -> bool:
        return self._resource.toggle_pin(resource_id)

    def toggle_favorite(self, resource_id: int) -> bool:
        return self._resource.toggle_favorite(resource_id)

    def delete_resource(self, resource_id: int) -> bool:
        return self._resource.delete_resource(resource_id)

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

    def create_highlight(
        self,
        resource_id: int,
        content: str,
        color: str | None = None,
        page: int | None = None,
        start_index: int | None = None,
        length: int | None = None,
    ) -> object:
        return self._highlight.create_highlight(resource_id, content, color, page, start_index, length)

    def update_highlight_color(self, highlight_id: int, color: str) -> object:
        return self._highlight.update_highlight_color(highlight_id, color)

    def update_highlight_comment(self, highlight_id: int, comment: str) -> object:
        return self._highlight.update_highlight_comment(highlight_id, comment)

    def delete_highlight(self, highlight_id: int) -> bool:
        return self._highlight.delete_highlight(highlight_id)

    def delete_highlights(self, highlight_ids: list[int]) -> int | None:
        return self._highlight.delete_highlights(highlight_ids)

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

    # ------------------------------------------------------------------ #
    # PDF Notu
    # ------------------------------------------------------------------ #

    def create_pdf_note(self, resource_id: int, page: int, x: float, y: float, note_text: str) -> object:
        return self._pdf_note.create_note(resource_id, page, x, y, note_text)

    def update_pdf_note(self, note_id: int, note_text: str) -> object:
        return self._pdf_note.update_note(note_id, note_text)

    def delete_pdf_note(self, note_id: int) -> bool:
        return self._pdf_note.delete_note(note_id)

    def load_resource_pdf_notes(self, resource_id: int) -> list:
        return self._pdf_note.load_resource_notes(resource_id)

    # ------------------------------------------------------------------ #
    # Kayitli aramalar (Makale Market)
    # ------------------------------------------------------------------ #

    def load_saved_searches(self) -> list:
        return self._saved_search.load_saved_searches()

    def create_saved_search(
        self, topic: str, filters: dict | None, tag_name: str | None, seen_ids: list[str] | None
    ) -> object:
        return self._saved_search.create_saved_search(topic, filters, tag_name, seen_ids)

    def delete_saved_search(self, search_id: int) -> bool:
        return self._saved_search.delete_saved_search(search_id)

    def mark_saved_search_seen(self, search_id: int, ids: list[str]) -> object:
        return self._saved_search.mark_saved_search_seen(search_id, ids)

    def record_saved_search_check(self, search_id: int, new_count: int) -> object:
        return self._saved_search.record_saved_search_check(search_id, new_count)

    def load_due_saved_searches(self, max_age) -> list:
        return self._saved_search.load_due_saved_searches(max_age)
