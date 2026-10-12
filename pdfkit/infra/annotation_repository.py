from sqlalchemy import select
from sqlalchemy.orm import Session

from pdfkit.domain.annotations import Annotation, PageNote, Segment, Term
from pdfkit.infra.orm import PdfAnnotationRow, PdfPageNoteRow, PdfTermRow


def segments_to_json(segments: list[Segment]) -> list[dict]:
    return [
        {
            "page": s.page,
            "start": s.start,
            "end": s.end,
            "text": s.text,
            **({"polygons": [[list(point) for point in polygon] for polygon in s.polygons]} if s.polygons else {}),
        }
        for s in segments
    ]


def segments_from_json(raw: list[dict] | None) -> list[Segment]:
    return [
        Segment(
            item["page"],
            item["start"],
            item["end"],
            item.get("text", ""),
            [[tuple(point) for point in polygon] for polygon in item["polygons"]] if item.get("polygons") else None,
        )
        for item in (raw or [])
    ]


def annotation_from_row(row: PdfAnnotationRow) -> Annotation:
    return Annotation(
        id=row.id, uid=row.uid, document_id=row.document_id, label_key=row.label_key, color=row.color,
        comment=row.comment, tags=list(row.tags or []), quote_exact=row.quote_exact,
        quote_prefix=row.quote_prefix, quote_suffix=row.quote_suffix, segments=segments_from_json(row.segments),
        engine_fp=row.engine_fp, status=row.anchor_status, created_at=row.created_at,
        updated_at=row.updated_at, legacy_id=row.legacy_id,
    )


def note_from_row(row: PdfPageNoteRow) -> PageNote:
    return PageNote(
        id=row.id, uid=row.uid, document_id=row.document_id, page=row.page, x=row.x, y=row.y, text=row.text,
        created_at=row.created_at, updated_at=row.updated_at, legacy_id=row.legacy_id,
    )


def term_from_row(row: PdfTermRow) -> Term:
    return Term(
        id=row.id, uid=row.uid, document_id=row.document_id, word=row.word, translation=row.translation,
        context_sentence=row.context_sentence, mastery_level=row.mastery_level,
        segments=segments_from_json(row.segments), status=row.anchor_status, engine_fp=row.engine_fp,
        created_at=row.created_at, legacy_id=row.legacy_id,
    )


class AnnotationRepository:
    """Alinti, sayfa notu ve kelime kayitlari. commit/rollback `AnnotationService`'tedir."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ---- alintilar ----
    def add_annotation(self, row: PdfAnnotationRow) -> Annotation:
        self._session.add(row)
        self._session.flush()
        return annotation_from_row(row)

    def get_annotation(self, annotation_id: int) -> PdfAnnotationRow | None:
        return self._session.get(PdfAnnotationRow, annotation_id)

    def annotation_by_uid(self, uid: str) -> PdfAnnotationRow | None:
        return self._session.scalar(select(PdfAnnotationRow).where(PdfAnnotationRow.uid == uid))

    def annotations_for_document(self, document_id: int) -> list[PdfAnnotationRow]:
        return list(
            self._session.scalars(
                select(PdfAnnotationRow)
                .where(PdfAnnotationRow.document_id == document_id)
                .order_by(PdfAnnotationRow.page, PdfAnnotationRow.id)
            )
        )

    def annotations_with_status(self, document_id: int, statuses: tuple[str, ...]) -> list[PdfAnnotationRow]:
        return list(
            self._session.scalars(
                select(PdfAnnotationRow).where(
                    PdfAnnotationRow.document_id == document_id, PdfAnnotationRow.anchor_status.in_(statuses)
                )
            )
        )

    def legacy_annotation_ids(self) -> dict[int, int]:
        """eski highlight id -> yeni satir id."""
        rows = self._session.execute(
            select(PdfAnnotationRow.legacy_id, PdfAnnotationRow.id).where(PdfAnnotationRow.legacy_id.is_not(None))
        )
        return {legacy: new for legacy, new in rows}

    # ---- sayfa notlari ----
    def add_note(self, row: PdfPageNoteRow) -> PageNote:
        self._session.add(row)
        self._session.flush()
        return note_from_row(row)

    def get_note(self, note_id: int) -> PdfPageNoteRow | None:
        return self._session.get(PdfPageNoteRow, note_id)

    def notes_for_document(self, document_id: int) -> list[PdfPageNoteRow]:
        return list(
            self._session.scalars(
                select(PdfPageNoteRow)
                .where(PdfPageNoteRow.document_id == document_id)
                .order_by(PdfPageNoteRow.page, PdfPageNoteRow.id)
            )
        )

    def legacy_note_ids(self) -> dict[int, int]:
        rows = self._session.execute(
            select(PdfPageNoteRow.legacy_id, PdfPageNoteRow.id).where(PdfPageNoteRow.legacy_id.is_not(None))
        )
        return {legacy: new for legacy, new in rows}

    # ---- kelimeler ----
    def add_term(self, row: PdfTermRow) -> Term:
        self._session.add(row)
        self._session.flush()
        return term_from_row(row)

    def get_term(self, term_id: int) -> PdfTermRow | None:
        return self._session.get(PdfTermRow, term_id)

    def terms_for_document(self, document_id: int) -> list[PdfTermRow]:
        return list(
            self._session.scalars(
                select(PdfTermRow).where(PdfTermRow.document_id == document_id).order_by(PdfTermRow.id)
            )
        )

    def legacy_term_ids(self) -> dict[int, int]:
        rows = self._session.execute(
            select(PdfTermRow.legacy_id, PdfTermRow.id).where(PdfTermRow.legacy_id.is_not(None))
        )
        return {legacy: new for legacy, new in rows}

    def delete(self, row: object) -> None:
        self._session.delete(row)
        self._session.flush()
