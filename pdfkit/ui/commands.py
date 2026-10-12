from collections.abc import Callable

from core.logger import log
from pdfkit.domain.anchoring import context_around
from pdfkit.domain.annotations import Segment
from pdfkit.domain.errors import PdfkitError
from pdfkit.domain.sentences import extract_sentence
from pdfkit.domain.text import sanitize_text
from pdfkit.ui import messages
from pdfkit.ui.library import PdfLibrary
from pdfkit.ui.pdf_text import current_engine_fp, segment_from_selection
from pdfkit.ui.session import DocumentSession

_CONTEXT_STORED = 128  # veritabaninda tutulan onceki/sonraki baglam uzunlugu


class AnnotationCommands:
    """Acik belgede yazma islemleri: alinti, sayfa notu, kelime. Servise yazar, modeli artimli gunceller
    (yalniz etkilenen satir), kullaniciya bildirim gonderir. Hata UI sinirinda yakalanir: islem basarisizsa
    0 / False doner ve hata bildirimi gonderilir.

    Alinti eklemede geometri secimden hazir gelir (`segment_from_selection`), ek hesap yapilmaz."""

    def __init__(
        self, session: DocumentSession, library: PdfLibrary, notify: Callable[[str, str], None]
    ) -> None:
        self._session = session
        self._library = library
        self._notify = notify

    # ------------------------------------------------------------------ #
    # Alintilar
    # ------------------------------------------------------------------ #

    def add_highlight(self, selection: dict, label_key: str) -> int:
        resolved = self._session.resolve_selection(selection)
        document = self._session.document
        if resolved is None or document is None:
            self._notify("error", messages.NO_SELECTION)
            return 0
        page, qt_selection = resolved
        segment = segment_from_selection(page, qt_selection)
        quote = segment.text.strip()
        existing = self._existing_at(segment)
        if existing is not None:  # Ayni metin tekrar alintilaniyor: yeni kayit yerine anlam etiketini guncelle.
            relabeled = self._relabel(existing.id, label_key)
            if relabeled:
                self._notify("info", messages.HIGHLIGHT_RELABELED)
            return relabeled

        before, after = context_around(self._session.provider.text_of(page), segment.start, segment.end)

        def create() -> int:
            created = self._library.annotations().create_highlight(
                document.id, quote, [segment], label_key,
                prefix=before[-_CONTEXT_STORED:] or None, suffix=after[:_CONTEXT_STORED] or None,
                engine_fp=current_engine_fp(),
            )
            self._session.annotations_model.upsert(created)
            self._notify("info", messages.HIGHLIGHT_SAVED)
            return created.id

        return self._guard(create, 0)

    def set_label(self, annotation_id: int, label_key: str) -> bool:
        return self._relabel(annotation_id, label_key) != 0

    def set_comment(self, annotation_id: int, comment: str) -> bool:
        return self._update(lambda: self._library.annotations().set_comment(annotation_id, comment))

    def set_tags(self, annotation_id: int, tags: list[str]) -> bool:
        return self._update(lambda: self._library.annotations().set_tags(annotation_id, tags))

    def delete(self, annotation_id: int) -> bool:
        def run() -> bool:
            self._library.annotations().delete_highlight(annotation_id)
            self._session.annotations_model.remove(annotation_id)
            self._notify("info", messages.HIGHLIGHT_DELETED)
            return True

        return self._guard(run, False)

    def delete_many(self, annotation_ids: list[int]) -> int:
        def run() -> int:
            count = self._library.annotations().delete_highlights(annotation_ids)
            self._session.annotations_model.remove_many(annotation_ids)
            if count:
                self._notify("info", messages.HIGHLIGHTS_DELETED_FMT.format(count=count))
            return count

        return self._guard(run, 0)

    # ------------------------------------------------------------------ #
    # Sayfa notlari
    # ------------------------------------------------------------------ #

    def add_note(self, page: int, x: float, y: float, text: str) -> int:
        document = self._session.document
        if document is None:
            return 0

        def run() -> int:
            note = self._library.annotations().create_note(document.id, page, x, y, text)
            self._session.notes_model.upsert(note)
            return note.id

        return self._guard(run, 0)

    def update_note(self, note_id: int, text: str) -> bool:
        def run() -> bool:
            self._session.notes_model.upsert(self._library.annotations().update_note(note_id, text))
            return True

        return self._guard(run, False)

    def delete_note(self, note_id: int) -> bool:
        def run() -> bool:
            self._library.annotations().delete_note(note_id)
            self._session.notes_model.remove(note_id)
            return True

        return self._guard(run, False)

    # ------------------------------------------------------------------ #
    # Kelimeler
    # ------------------------------------------------------------------ #

    def add_term(self, selection: dict, translation: str) -> int:
        resolved = self._session.resolve_selection(selection)
        document = self._session.document
        if resolved is None or document is None:
            self._notify("error", messages.NO_SELECTION)
            return 0
        page, qt_selection = resolved
        segment = segment_from_selection(page, qt_selection)
        word = " ".join(sanitize_text(segment.text).split())
        sentence = extract_sentence(self._session.provider.text_of(page), segment.start, segment.end - segment.start)

        def run() -> int:
            term = self._library.annotations().create_term(
                document.id, word, translation, sentence, [segment], current_engine_fp()
            )
            self._session.reload_terms()
            self._notify("info", messages.TERM_SAVED_FMT.format(word=word))
            return term.id

        return self._guard(run, 0)

    def delete_term(self, term_id: int) -> bool:
        def run() -> bool:
            self._library.annotations().delete_term(term_id)
            self._session.reload_terms()
            self._notify("info", messages.TERM_DELETED)
            return True

        return self._guard(run, False)

    # ------------------------------------------------------------------ #
    # Yardimcilar
    # ------------------------------------------------------------------ #

    def _existing_at(self, segment: Segment):
        for annotation in self._session.annotations_model.annotations_on_page(segment.page):
            only = annotation.segments[0] if len(annotation.segments) == 1 else None
            if only and (only.page, only.start, only.end) == (segment.page, segment.start, segment.end):
                return annotation
        return None

    def _relabel(self, annotation_id: int, label_key: str) -> int:
        def run() -> int:
            # Etiket degisince acik renk gecersiz olur; renk etiketten turetilir.
            updated = self._library.annotations().set_label(annotation_id, label_key, None)
            self._session.annotations_model.upsert(updated)
            return updated.id

        return self._guard(run, 0)

    def _update(self, change: Callable[[], object]) -> bool:
        def run() -> bool:
            self._session.annotations_model.upsert(change())
            return True

        return self._guard(run, False)

    def _guard(self, run: Callable[[], object], failure):
        try:
            return run()
        except PdfkitError as exc:
            self._notify("error", str(exc))
        except Exception:
            log.exception("pdfkit islemi basarisiz")
            self._notify("error", messages.OPERATION_FAILED)
        return failure
