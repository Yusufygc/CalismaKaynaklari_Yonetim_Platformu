from PySide6.QtCore import Property, QObject, Signal, Slot

from core.constants.highlight_labels import HIGHLIGHT_LABELS
from core.constants.strings import AppStrings
from core.events import event_bus
from services.schemas import HighlightPosition
from ui_qml.bridges.reader_bridge import ReaderBridge
from ui_qml.context import BridgeContext
from ui_qml.serializers import DEFAULT_HIGHLIGHT_COLOR, serialize_pool_highlight, serialize_pool_vocabulary
from utils.text_utils import extract_sentence, sanitize_utf8


def _position_from_map(position: dict | None) -> HighlightPosition | None:
    if not position:
        return None
    page, start, length = (position.get(k, -1) for k in ("page", "startIndex", "length"))
    if page < 0 or start < 0 or length < 0:
        return None
    return HighlightPosition(int(page), int(start), int(length))


class AnnotationsBridge(QObject):
    """Okuyucudaki kullanici notlari: alintilar (HTML/PDF), kelime havuzu ve PDF sayfa notlari. Acik okuyucu
    kaynagini tazelemek icin `ReaderBridge.refresh_current`'i kullanir."""

    highlightsChanged = Signal()
    vocabularyChanged = Signal()

    def __init__(self, ctx: BridgeContext, reader: ReaderBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._reader = reader
        self._highlights_cache: list[dict] = []
        self._vocabulary_cache: list[dict] = []
        event_bus.highlight_added.connect(self.reload_highlights)
        event_bus.highlight_deleted.connect(self.reload_highlights)
        event_bus.vocabulary_added.connect(self.reload_vocabulary)
        event_bus.vocabulary_deleted.connect(self.reload_vocabulary)

    @Property(list, notify=highlightsChanged)
    def highlights(self) -> list:
        return self._highlights_cache

    @Property(list, notify=vocabularyChanged)
    def vocabulary(self) -> list:
        return self._vocabulary_cache

    @Property(list, constant=True)
    def highlightLabels(self) -> list:
        return HIGHLIGHT_LABELS

    def refresh(self) -> None:
        self.reload_highlights()
        self.reload_vocabulary()

    def reload_highlights(self, _id: int = 0) -> None:
        self._highlights_cache = [
            serialize_pool_highlight(h) for h in self._ctx.controllers.highlights.load_all_highlights()
        ]
        self.highlightsChanged.emit()

    def reload_vocabulary(self, _id: int = 0) -> None:
        self._vocabulary_cache = [
            serialize_pool_vocabulary(v) for v in self._ctx.controllers.vocabulary.load_all_vocabulary()
        ]
        self.vocabularyChanged.emit()

    # ------------------------------------------------------------------ #
    # Alinti
    # ------------------------------------------------------------------ #

    @Slot(int, str, str)
    @Slot(int, str, str, "QVariantMap")
    def addHighlight(
        self,
        resource_id: int,
        content: str,
        color: str = DEFAULT_HIGHLIGHT_COLOR,
        position: dict | None = None,
    ) -> None:
        """HTML okuyucudan alinti ekler. `position` (opsiyonel): {page, startIndex, length}."""
        if not content.strip():
            return
        self._save_highlight(resource_id, content.strip(), color, _position_from_map(position))

    def _save_highlight(
        self, resource_id: int, content: str, color: str, position: HighlightPosition | None
    ) -> None:
        result = self._ctx.controllers.highlights.create_highlight(resource_id, content, color, position)
        if result is None:
            return  # Hata zaten event_bus.error_occurred uzerinden toast olarak gosterildi
        self.reload_highlights()
        self._reader.refresh_current(resource_id)
        self._ctx.notify.info(AppStrings.NOTIFICATION_HIGHLIGHT_SAVED)

    @Slot(int, str, "QVariantMap", str)
    def addPdfHighlight(self, resource_id: int, file_url: str, selection: dict, color: str) -> None:
        """PDF'te secili metni alinti olarak kaydeder. `selection`: {page, fromX, fromY, toX, toY}."""
        resolved = self._ctx.pdf_files.select_text(file_url, selection)
        if resolved is None:
            return
        _doc, page, pdf_selection = resolved
        start = pdf_selection.startIndex()
        position = HighlightPosition(page, start, pdf_selection.endIndex() - start)
        self._save_highlight(resource_id, sanitize_utf8(pdf_selection.text()), color, position)

    @Slot(int, str)
    def updateHighlightColor(self, highlight_id: int, color: str) -> None:
        if self._ctx.controllers.highlights.update_highlight_color(highlight_id, color) is None:
            return
        self.reload_highlights()
        self._reader.refresh_current()

    @Slot(int, str)
    def updateHighlightComment(self, highlight_id: int, comment: str) -> None:
        if self._ctx.controllers.highlights.update_highlight_comment(highlight_id, comment) is None:
            return
        self.reload_highlights()
        self._reader.refresh_current()

    @Slot(int)
    def deleteHighlight(self, highlight_id: int) -> None:
        if not self._ctx.controllers.highlights.delete_highlight(highlight_id):
            return
        self.reload_highlights()
        self._reader.refresh_current()
        self._ctx.notify.info(AppStrings.NOTIFICATION_HIGHLIGHT_DELETED)

    @Slot("QVariantList")
    def deleteHighlights(self, highlight_ids: list) -> None:
        """Secili alintilari toplu siler (tek yenileme, tek bildirim)."""
        deleted = self._ctx.controllers.highlights.delete_highlights([int(i) for i in highlight_ids])
        if not deleted:
            return
        self.reload_highlights()
        self._reader.refresh_current()
        self._ctx.notify.info(AppStrings.NOTIFICATION_HIGHLIGHTS_DELETED_FMT.format(count=deleted))

    # ------------------------------------------------------------------ #
    # Kelime
    # ------------------------------------------------------------------ #

    @Slot(int, str, str, str)
    def addVocabulary(self, resource_id: int, word: str, translation: str, context_sentence: str = "") -> None:
        if not word.strip() or not translation.strip():
            return
        result = self._ctx.controllers.vocabulary.create_vocabulary(
            resource_id, word.strip(), translation.strip(), context_sentence.strip() or None
        )
        if result is None:
            return
        self.reload_vocabulary()
        self._ctx.notify.info(AppStrings.NOTIFICATION_VOCAB_SAVED_FMT.format(word=word))

    @Slot(int)
    def deleteVocabulary(self, vocabulary_id: int) -> None:
        if not self._ctx.controllers.vocabulary.delete_vocabulary(vocabulary_id):
            return
        self.reload_vocabulary()
        self._ctx.notify.info(AppStrings.NOTIFICATION_VOCAB_DELETED)

    @Slot(int, str, "QVariantMap", str)
    def addPdfVocabulary(self, resource_id: int, file_url: str, selection: dict, translation: str) -> None:
        """PDF'te secili kelimeyi, gectigi cumleyle (baglam) birlikte kelime havuzuna ekler.
        `selection`: {page, fromX, fromY, toX, toY} (bkz. `PdfFileManager.select_text`)."""
        resolved = self._ctx.pdf_files.select_text(file_url, selection)
        if resolved is None:
            return
        doc, page, pdf_selection = resolved
        word = sanitize_utf8(pdf_selection.text()).strip()
        page_text = sanitize_utf8(doc.getSelectionAtIndex(page, 0, 1_000_000).text())
        start = pdf_selection.startIndex()
        context = extract_sentence(page_text, start, pdf_selection.endIndex() - start)
        self.addVocabulary(resource_id, " ".join(word.split()), translation, context)

    # ------------------------------------------------------------------ #
    # PDF notu
    # ------------------------------------------------------------------ #

    @Slot(int, int, float, float, str)
    def addPdfNote(self, resource_id: int, page: int, x: float, y: float, text: str) -> None:
        if not text.strip():
            return
        if self._ctx.controllers.pdf_notes.create_note(resource_id, page, x, y, text.strip()) is None:
            return
        self._reader.refresh_current(resource_id)

    @Slot(int, str)
    def updatePdfNote(self, note_id: int, text: str) -> None:
        if not text.strip():
            return
        if self._ctx.controllers.pdf_notes.update_note(note_id, text.strip()) is None:
            return
        self._reader.refresh_current()

    @Slot(int)
    def deletePdfNote(self, note_id: int) -> None:
        if self._ctx.controllers.pdf_notes.delete_note(note_id):
            self._reader.refresh_current()
