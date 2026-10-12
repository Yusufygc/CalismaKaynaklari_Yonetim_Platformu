from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from sqlalchemy.orm import Session

from core.logger import log
from pdfkit.domain.anchoring import PageTextProvider, Resolution, resolve
from pdfkit.domain.annotations import (
    STATUS_OK,
    STATUS_ORPHANED,
    STATUS_PENDING,
    STATUS_UNANCHORED,
    Annotation,
    PageNote,
    Segment,
    Term,
)
from pdfkit.domain.errors import InvalidAnnotationError, NotFoundError
from pdfkit.domain.ids import new_uid
from pdfkit.domain.labels import is_known_label
from pdfkit.domain.text import sanitize_text
from pdfkit.infra.annotation_repository import (
    AnnotationRepository,
    annotation_from_row,
    note_from_row,
    segments_from_json,
    segments_to_json,
    term_from_row,
)
from pdfkit.infra.orm import PdfAnnotationRow, PdfPageNoteRow, PdfTermRow
from pdfkit.infra.repository import DocumentRepository

T = TypeVar("T")


@dataclass(frozen=True)
class BackfillReport:
    resolved: int  # konumu dogrulanan (baglami cikarilan) alinti
    moved: int  # bunlardan konumu degisen
    orphaned: int  # metni bulunamayan


class AnnotationService:
    """Alinti, sayfa notu ve kelime kayitlari. commit/rollback bu katmandadir (projenin oturum kurali)."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = AnnotationRepository(session)
        self._documents = DocumentRepository(session)

    # ------------------------------------------------------------------ #
    # Alintilar
    # ------------------------------------------------------------------ #

    def create_highlight(
        self,
        document_id: int,
        quote_exact: str,
        segments: list[Segment],
        label_key: str = "general",
        *,
        color: str | None = None,
        comment: str | None = None,
        tags: list[str] | None = None,
        prefix: str | None = None,
        suffix: str | None = None,
        engine_fp: str | None = None,
        status: str = STATUS_OK,
    ) -> Annotation:
        quote = sanitize_text(quote_exact).strip()
        if not quote:
            raise InvalidAnnotationError("Alinti metni bos olamaz.")
        if not segments:
            raise InvalidAnnotationError("Alinti en az bir parca (sayfa konumu) icermeli.")
        if not is_known_label(label_key):
            raise InvalidAnnotationError(f"Bilinmeyen anlam etiketi: {label_key}")
        self._require_document(document_id)
        row = PdfAnnotationRow(
            uid=new_uid(),
            document_id=document_id,
            label_key=label_key,
            color=color,
            comment=sanitize_text(comment).strip() or None,
            tags=_clean_tags(tags),
            quote_exact=quote,
            quote_prefix=prefix,
            quote_suffix=suffix,
            page=segments[0].page,
            segments=segments_to_json(segments),
            engine_fp=engine_fp,
            anchor_status=status,
        )
        return self._write(lambda: self._repo.add_annotation(row))

    def list_highlights(self, document_id: int) -> list[Annotation]:
        return [annotation_from_row(row) for row in self._repo.annotations_for_document(document_id)]

    def get_highlight(self, annotation_id: int) -> Annotation:
        return annotation_from_row(self._annotation_row(annotation_id))

    def set_label(self, annotation_id: int, label_key: str, color: str | None = None) -> Annotation:
        if not is_known_label(label_key):
            raise InvalidAnnotationError(f"Bilinmeyen anlam etiketi: {label_key}")

        def change() -> Annotation:
            row = self._annotation_row(annotation_id)
            row.label_key, row.color = label_key, color
            return annotation_from_row(row)

        return self._write(change)

    def set_comment(self, annotation_id: int, comment: str | None) -> Annotation:
        def change() -> Annotation:
            row = self._annotation_row(annotation_id)
            row.comment = (comment or "").strip() or None
            return annotation_from_row(row)

        return self._write(change)

    def set_tags(self, annotation_id: int, tags: list[str]) -> Annotation:
        def change() -> Annotation:
            row = self._annotation_row(annotation_id)
            row.tags = _clean_tags(tags)
            return annotation_from_row(row)

        return self._write(change)

    def delete_highlight(self, annotation_id: int) -> None:
        self._write(lambda: self._repo.delete(self._annotation_row(annotation_id)))

    def delete_highlights(self, annotation_ids: list[int]) -> int:
        """Birden cok alintiyi tek islemde siler; silinen sayisini dondurur (olmayan kimlikler atlanir)."""

        def change() -> int:
            count = 0
            for annotation_id in annotation_ids:
                row = self._repo.get_annotation(annotation_id)
                if row is not None:
                    self._repo.delete(row)
                    count += 1
            return count

        return self._write(change)

    def relink(
        self, annotation_id: int, segments: list[Segment], quote_exact: str,
        prefix: str | None, suffix: str | None, engine_fp: str | None,
    ) -> Annotation:
        """Yetim alintiyi kullanicinin yeniden sectigi metne baglar."""
        if not segments or not quote_exact.strip():
            raise InvalidAnnotationError("Yeniden baglama icin metin ve konum gerekli.")

        def change() -> Annotation:
            row = self._annotation_row(annotation_id)
            row.quote_exact, row.quote_prefix, row.quote_suffix = quote_exact.strip(), prefix, suffix
            _apply_segments(row, segments, engine_fp, STATUS_OK)
            return annotation_from_row(row)

        return self._write(change)

    def apply_resolution(self, annotation_id: int, resolution: Resolution, engine_fp: str | None) -> Annotation:
        def change() -> Annotation:
            row = self._annotation_row(annotation_id)
            if resolution.status == STATUS_OK:
                if resolution.prefix is not None:
                    row.quote_prefix = resolution.prefix[-128:]
                if resolution.suffix is not None:
                    row.quote_suffix = resolution.suffix[:128]
                _apply_segments(row, resolution.segments, engine_fp, STATUS_OK)
            else:
                row.anchor_status = STATUS_ORPHANED
            return annotation_from_row(row)

        return self._write(change)

    def store_geometry(self, updates: dict[int, list[Segment]], engine_fp: str | None) -> list[Annotation]:
        """Hesaplanan sayfa-noktasi poligonlarini alintilara kalici yazar (belge basina bir kez; sonraki
        acilislarda hesap gerekmez). `updates`: alinti kimligi -> poligonlu parcalar."""

        def change() -> list[Annotation]:
            stored = []
            for annotation_id, segments in updates.items():
                row = self._repo.get_annotation(annotation_id)
                if row is None:
                    continue
                row.segments = segments_to_json(segments)
                row.engine_fp = engine_fp
                stored.append(annotation_from_row(row))
            return stored

        return self._write(change)

    def backfill_context(self, document_id: int, provider: PageTextProvider, engine_fp: str | None) -> BackfillReport:
        """Eski kayitlarin (konum var, baglam yok) konumunu dogrular ve onceki/sonraki baglami cikarir.
        Belge ilk acildiginda Qt metin saglayicisiyla cagrilir."""
        resolved = moved = orphaned = 0

        def change() -> None:
            nonlocal resolved, moved, orphaned
            for row in self._repo.annotations_with_status(document_id, (STATUS_PENDING,)):
                resolution = resolve(_segments(row), row.quote_prefix, row.quote_suffix, provider)
                if resolution.status == STATUS_OK:
                    row.quote_prefix = (resolution.prefix or "")[-128:] or None
                    row.quote_suffix = (resolution.suffix or "")[:128] or None
                    _apply_segments(row, resolution.segments, engine_fp, STATUS_OK)
                    resolved += 1
                    moved += 1 if resolution.moved else 0
                else:
                    row.anchor_status = STATUS_ORPHANED
                    orphaned += 1

        self._write(change)
        return BackfillReport(resolved, moved, orphaned)

    # ------------------------------------------------------------------ #
    # Sayfa notlari
    # ------------------------------------------------------------------ #

    def create_note(self, document_id: int, page: int, x: float, y: float, text: str) -> PageNote:
        if not (text or "").strip():
            raise InvalidAnnotationError("Not metni bos olamaz.")
        if page < 0:
            raise InvalidAnnotationError("Sayfa numarasi negatif olamaz.")
        self._require_document(document_id)
        row = PdfPageNoteRow(uid=new_uid(), document_id=document_id, page=page, x=x, y=y, text=text.strip())
        return self._write(lambda: self._repo.add_note(row))

    def list_notes(self, document_id: int) -> list[PageNote]:
        return [note_from_row(row) for row in self._repo.notes_for_document(document_id)]

    def update_note(self, note_id: int, text: str) -> PageNote:
        if not (text or "").strip():
            raise InvalidAnnotationError("Not metni bos olamaz.")

        def change() -> PageNote:
            row = self._note_row(note_id)
            row.text = text.strip()
            return note_from_row(row)

        return self._write(change)

    def delete_note(self, note_id: int) -> None:
        self._write(lambda: self._repo.delete(self._note_row(note_id)))

    # ------------------------------------------------------------------ #
    # Kelimeler
    # ------------------------------------------------------------------ #

    def create_term(
        self, document_id: int, word: str, translation: str, context_sentence: str | None = None,
        segments: list[Segment] | None = None, engine_fp: str | None = None,
    ) -> Term:
        if not (word or "").strip() or not (translation or "").strip():
            raise InvalidAnnotationError("Kelime ve anlami bos olamaz.")
        self._require_document(document_id)
        segments = segments or []
        row = PdfTermRow(
            uid=new_uid(), document_id=document_id, word=word.strip(), translation=translation.strip(),
            context_sentence=(context_sentence or "").strip() or None, mastery_level=0,
            page=segments[0].page if segments else None, segments=segments_to_json(segments), engine_fp=engine_fp,
            anchor_status=STATUS_OK if segments else STATUS_UNANCHORED,
        )
        return self._write(lambda: self._repo.add_term(row))

    def list_terms(self, document_id: int) -> list[Term]:
        return [term_from_row(row) for row in self._repo.terms_for_document(document_id)]

    def delete_term(self, term_id: int) -> None:
        def change() -> None:
            row = self._repo.get_term(term_id)
            if row is None:
                raise NotFoundError(f"Kelime bulunamadi: id={term_id}")
            self._repo.delete(row)

        self._write(change)

    # ------------------------------------------------------------------ #
    # Yardimcilar
    # ------------------------------------------------------------------ #

    def _write(self, change: Callable[[], T]) -> T:
        try:
            result = change()
            self._session.commit()
            return result
        except Exception:
            self._session.rollback()
            raise

    def _require_document(self, document_id: int) -> None:
        if self._documents.get_by_id(document_id) is None:
            raise NotFoundError(f"Belge bulunamadi: id={document_id}")

    def _annotation_row(self, annotation_id: int) -> PdfAnnotationRow:
        row = self._repo.get_annotation(annotation_id)
        if row is None:
            raise NotFoundError(f"Alinti bulunamadi: id={annotation_id}")
        return row

    def _note_row(self, note_id: int) -> PdfPageNoteRow:
        row = self._repo.get_note(note_id)
        if row is None:
            raise NotFoundError(f"Not bulunamadi: id={note_id}")
        return row


def _clean_tags(tags: list[str] | None) -> list[str]:
    seen: list[str] = []
    for tag in tags or []:
        name = tag.strip().lstrip("#").strip().lower()
        if name and name not in seen:
            seen.append(name)
    return seen


def _segments(row: PdfAnnotationRow) -> list[Segment]:
    return segments_from_json(row.segments)


def _apply_segments(row: PdfAnnotationRow, segments: list[Segment], engine_fp: str | None, status: str) -> None:
    row.segments = segments_to_json(segments)
    row.page = segments[0].page
    row.engine_fp = engine_fp
    row.anchor_status = status
    log.debug("Alinti capasi guncellendi: uid=%s durum=%s", row.uid, status)
