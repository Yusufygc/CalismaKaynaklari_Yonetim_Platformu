"""Eski `highlights` / `pdf_notes` / `vocabulary` tablolarindaki PDF kayitlarini pdfkit tablolarina kopyalar.

GECICI kopru (Faz 8'e kadar): arayuz Faz 3'te pdfkit'e gecene dek eski tablolar canli veri kaynagidir. Bu yuzden
kopyalama tekrar calistirilabilir (idempotent) ve eski tablodaki degisiklikleri (yorum, renk, silme) yansitir;
`legacy_id` bos olan (pdfkit'te dogrudan olusturulmus) kayitlara dokunmaz. Eski tablolar silinmez. Yalnizca PDF
belgesine baglanmis kaynaklarin kayitlari kopyalanir; HTML makale alintilari eski tabloda kalir.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from core.logger import log
from pdfkit.domain.annotations import STATUS_PENDING, STATUS_UNANCHORED, Segment
from pdfkit.domain.ids import new_uid
from pdfkit.domain.labels import label_key_for_color
from pdfkit.domain.text import sanitize_text
from pdfkit.infra.annotation_repository import AnnotationRepository, segments_to_json
from pdfkit.infra.orm import PdfAnnotationRow, PdfPageNoteRow, PdfTermRow

_HIGHLIGHTS = text(
    "SELECT h.id, d.document_id, h.content, h.page_number, h.color, h.start_index, h.length, h.comment, "
    "h.created_at FROM highlights h JOIN pdf_resource_documents d ON d.resource_id = h.resource_id "
    "WHERE h.page_number IS NOT NULL AND h.start_index IS NOT NULL AND h.length > 0"
)
_NOTES = text(
    "SELECT n.id, d.document_id, n.page, n.x, n.y, n.note_text, n.created_at FROM pdf_notes n "
    "JOIN pdf_resource_documents d ON d.resource_id = n.resource_id"
)
_TERMS = text(
    "SELECT v.id, d.document_id, v.word, v.translation, v.context_sentence, v.mastery_level, v.created_at "
    "FROM vocabulary v JOIN pdf_resource_documents d ON d.resource_id = v.resource_id"
)


@dataclass(frozen=True)
class LegacyImportReport:
    added: int
    updated: int
    removed: int


def _timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    parsed = datetime.fromisoformat(str(value).replace(" ", "T"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class LegacyAnnotationImporter:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = AnnotationRepository(session)

    def run(self, delete_missing: bool = True) -> LegacyImportReport:
        """Kopyalar/gunceller (ve `delete_missing` ise eski tabloda artik olmayanlari siler); tek islemde commit."""
        added = updated = removed = 0
        try:
            for sync in (self._sync_highlights, self._sync_notes, self._sync_terms):
                a, u, r = sync(delete_missing)
                added, updated, removed = added + a, updated + u, removed + r
            self._session.commit()
        except Exception:
            self._session.rollback()
            log.exception("Eski PDF kayitlari pdfkit'e kopyalanamadi.")
            raise
        if added or updated or removed:
            log.info("Eski PDF kayitlari esitlendi: +%d ~%d -%d", added, updated, removed)
        return LegacyImportReport(added, updated, removed)

    def _sync_highlights(self, delete_missing: bool) -> tuple[int, int, int]:
        existing = self._repo.legacy_annotation_ids()
        seen, added, updated = set(), 0, 0
        for row in self._session.execute(_HIGHLIGHTS):
            legacy_id, document_id, content, page, color, start, length, comment, created = row
            seen.add(legacy_id)
            quote = sanitize_text(content).strip()
            if not quote:
                continue
            label = label_key_for_color(color)
            if legacy_id in existing:
                target = self._repo.get_annotation(existing[legacy_id])
                values = (color, label, sanitize_text(comment).strip() or None)
                updated += 1 if (target.color, target.label_key, target.comment) != values else 0
                target.color, target.label_key, target.comment = values
                continue
            self._repo.add_annotation(
                PdfAnnotationRow(
                    uid=new_uid(), document_id=document_id, label_key=label, color=color,
                    comment=sanitize_text(comment).strip() or None, tags=[], quote_exact=quote,
                    page=page, segments=segments_to_json([Segment(page, start, start + length, quote)]),
                    anchor_status=STATUS_PENDING, created_at=_timestamp(created), legacy_id=legacy_id,
                )
            )
            added += 1
        removed = self._remove_missing(existing, seen, self._repo.get_annotation) if delete_missing else 0
        return added, updated, removed

    def _sync_notes(self, delete_missing: bool) -> tuple[int, int, int]:
        existing = self._repo.legacy_note_ids()
        seen, added, updated = set(), 0, 0
        for legacy_id, document_id, page, x, y, note_text, created in self._session.execute(_NOTES):
            seen.add(legacy_id)
            body = sanitize_text(note_text).strip()
            if legacy_id in existing:
                target = self._repo.get_note(existing[legacy_id])
                updated += 1 if target.text != body else 0
                target.text = body
                continue
            self._repo.add_note(
                PdfPageNoteRow(
                    uid=new_uid(), document_id=document_id, page=page, x=x, y=y, text=body,
                    created_at=_timestamp(created), legacy_id=legacy_id,
                )
            )
            added += 1
        removed = self._remove_missing(existing, seen, self._repo.get_note) if delete_missing else 0
        return added, updated, removed

    def _sync_terms(self, delete_missing: bool) -> tuple[int, int, int]:
        existing = self._repo.legacy_term_ids()
        seen, added, updated = set(), 0, 0
        for legacy_id, document_id, word, translation, sentence, mastery, created in self._session.execute(_TERMS):
            seen.add(legacy_id)
            if legacy_id in existing:
                target = self._repo.get_term(existing[legacy_id])
                clean = sanitize_text(translation)
                updated += 1 if target.translation != clean else 0
                target.translation = clean
                continue
            self._repo.add_term(
                PdfTermRow(
                    uid=new_uid(), document_id=document_id, word=sanitize_text(word), translation=sanitize_text(translation),
                    context_sentence=sanitize_text(sentence).strip() or None, mastery_level=mastery or 0,
                    page=None, segments=[], anchor_status=STATUS_UNANCHORED, created_at=_timestamp(created),
                    legacy_id=legacy_id,
                )
            )
            added += 1
        removed = self._remove_missing(existing, seen, self._repo.get_term) if delete_missing else 0
        return added, updated, removed

    def _remove_missing(self, existing: dict[int, int], seen: set[int], getter) -> int:
        removed = 0
        for legacy_id, new_id in existing.items():
            if legacy_id not in seen:
                row = getter(new_id)
                if row is not None:
                    self._repo.delete(row)
                    removed += 1
        return removed
