from collections import Counter

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from core.constants.highlight_labels import HIGHLIGHT_LABELS
from core.constants.strings import AppStrings
from core.events import event_bus
from pdfkit.api import PdfkitError
from services.schemas import HighlightPosition
from ui_qml.bridges.reader_bridge import ReaderBridge
from ui_qml.context import BridgeContext
from ui_qml.serializers import (
    DEFAULT_HIGHLIGHT_COLOR,
    serialize_pool_highlight,
    serialize_pool_pdf_highlight,
    serialize_pool_pdf_term,
    serialize_pool_vocabulary,
)

_REFRESH_DELAY_MS = 150  # Art arda yazmalarda (PDF'te hizli alinti ekleme) havuz tek seferde tazelenir.
PDF_KEY_PREFIX, HTML_KEY_PREFIX = "pdf:", "html:"


def _position_from_map(position: dict | None) -> HighlightPosition | None:
    if not position:
        return None
    page, start, length = (position.get(k, -1) for k in ("page", "startIndex", "length"))
    if page < 0 or start < 0 or length < 0:
        return None
    return HighlightPosition(int(page), int(start), int(length))


def _split_key(key: str) -> tuple[str, int]:
    """Bilgi Havuzu anahtari ('pdf:12' / 'html:7') -> (kaynak, kimlik). Gecersizse ('', 0)."""
    for prefix in (PDF_KEY_PREFIX, HTML_KEY_PREFIX):
        if str(key).startswith(prefix):
            try:
                return prefix, int(str(key)[len(prefix):])
            except ValueError:
                break
    return "", 0


class AnnotationsBridge(QObject):
    """Bilgi Havuzu (kitaplik geneli alinti/kelime listesi) ve HTML makale okuyucusunun alintilari/kelimeleri.

    PDF belgelerinin alinti/not/kelimeleri `PdfBridge`'dedir (pdfkit); havuz her ikisini birlestirir ve her
    ogeye kaynagini belirten bir `key` ('pdf:<id>' ya da 'html:<id>') verir, silme bu anahtarla yapilir."""

    highlightsChanged = Signal()
    vocabularyChanged = Signal()

    def __init__(self, ctx: BridgeContext, reader: ReaderBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._reader = reader
        self._highlights_cache: list[dict] = []
        self._vocabulary_cache: list[dict] = []
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(_REFRESH_DELAY_MS)
        self._refresh_timer.timeout.connect(self.refresh)
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

    @Property(list, notify=highlightsChanged)
    def highlightTags(self) -> list:
        """Havuzdaki serbest etiketler: [{name, count}] (sik kullanilandan aza, esitlikte ada gore)."""
        counts = Counter(tag for item in self._highlights_cache for tag in item.get("tags", []))
        return [{"name": name, "count": count} for name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    @Property(list, constant=True)
    def highlightLabels(self) -> list:
        return HIGHLIGHT_LABELS

    def refresh(self) -> None:
        self.reload_highlights()
        self.reload_vocabulary()

    def schedule_refresh(self) -> None:
        """Havuzu kisa bir gecikmeyle (birlestirerek) tazeler; sik yazma yollarinda UI thread'i bloklamaz."""
        self._refresh_timer.start()

    def reload_highlights(self, _id: int = 0) -> None:
        pdf_entries = self._ctx.pdf_library.annotations().pool_highlights()
        items = [serialize_pool_highlight(h) for h in self._ctx.controllers.highlights.load_all_highlights()]
        items += [serialize_pool_pdf_highlight(entry) for entry in pdf_entries]
        self._highlights_cache = items
        self.highlightsChanged.emit()

    def reload_vocabulary(self, _id: int = 0) -> None:
        pdf_entries = self._ctx.pdf_library.annotations().pool_terms()
        items = [serialize_pool_vocabulary(v) for v in self._ctx.controllers.vocabulary.load_all_vocabulary()]
        items += [serialize_pool_pdf_term(entry) for entry in pdf_entries]
        self._vocabulary_cache = items
        self.vocabularyChanged.emit()

    # ------------------------------------------------------------------ #
    # HTML makale okuyucusu: alinti
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
        result = self._ctx.controllers.highlights.create_highlight(
            resource_id, content.strip(), color, _position_from_map(position)
        )
        if result is None:
            return  # Hata zaten event_bus.error_occurred uzerinden toast olarak gosterildi
        self.reload_highlights()
        self._reader.refresh_current(resource_id)
        self._ctx.notify.info(AppStrings.NOTIFICATION_HIGHLIGHT_SAVED)

    @Slot(str)
    def deleteHighlight(self, key: str) -> None:
        source, item_id = _split_key(key)
        if source == PDF_KEY_PREFIX:
            if not self._delete_pdf(lambda service: service.delete_highlight(item_id)):
                return
        elif source == HTML_KEY_PREFIX:
            if not self._ctx.controllers.highlights.delete_highlight(item_id):
                return
        else:
            return
        self._after_highlight_delete()
        self._ctx.notify.info(AppStrings.NOTIFICATION_HIGHLIGHT_DELETED)

    @Slot("QVariantList")
    def deleteHighlights(self, keys: list) -> None:
        """Secili alintilari toplu siler (tek yenileme, tek bildirim)."""
        pdf_ids, html_ids = self._split_keys(keys)
        deleted = 0
        if pdf_ids:
            deleted += self._delete_pdf(lambda service: service.delete_highlights(pdf_ids)) or 0
        if html_ids:
            deleted += self._ctx.controllers.highlights.delete_highlights(html_ids) or 0
        if not deleted:
            return
        self._after_highlight_delete()
        self._ctx.notify.info(AppStrings.NOTIFICATION_HIGHLIGHTS_DELETED_FMT.format(count=deleted))

    def _after_highlight_delete(self) -> None:
        self.reload_highlights()
        self._reader.refresh_current()

    def _delete_pdf(self, delete):
        """pdfkit servis silmesini UI sinirinda calistirir; hata kullaniciya bildirilir, basarida sonucu (ya da True) dondurur."""
        try:
            result = delete(self._ctx.pdf_library.annotations())
        except PdfkitError as exc:
            self._ctx.notify.error(str(exc))
            return False
        return True if result is None else result

    @staticmethod
    def _split_keys(keys: list) -> tuple[list[int], list[int]]:
        pdf_ids, html_ids = [], []
        for key in keys:
            source, item_id = _split_key(key)
            if source == PDF_KEY_PREFIX:
                pdf_ids.append(item_id)
            elif source == HTML_KEY_PREFIX:
                html_ids.append(item_id)
        return pdf_ids, html_ids

    # ------------------------------------------------------------------ #
    # Kelime
    # ------------------------------------------------------------------ #

    @Slot(int, str, str, str)
    def addVocabulary(self, resource_id: int, word: str, translation: str, context_sentence: str = "") -> None:
        """HTML okuyucudan kelime ekler (PDF'te kelime `bridge.pdf.addTerm` ile eklenir)."""
        if not word.strip() or not translation.strip():
            return
        result = self._ctx.controllers.vocabulary.create_vocabulary(
            resource_id, word.strip(), translation.strip(), context_sentence.strip() or None
        )
        if result is None:
            return
        self.reload_vocabulary()
        self._ctx.notify.info(AppStrings.NOTIFICATION_VOCAB_SAVED_FMT.format(word=word))

    @Slot(str)
    def deleteVocabulary(self, key: str) -> None:
        source, item_id = _split_key(key)
        if source == PDF_KEY_PREFIX:
            if not self._delete_pdf(lambda service: service.delete_term(item_id)):
                return
        elif source == HTML_KEY_PREFIX:
            if not self._ctx.controllers.vocabulary.delete_vocabulary(item_id):
                return
        else:
            return
        self.reload_vocabulary()
        self._ctx.notify.info(AppStrings.NOTIFICATION_VOCAB_DELETED)
