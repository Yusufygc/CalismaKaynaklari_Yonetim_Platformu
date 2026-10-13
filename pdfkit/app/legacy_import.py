"""Eski `highlights` / `pdf_notes` / `vocabulary` tablolarindaki PDF kayitlarini pdfkit tablolarina tasir.

Arayuz pdfkit'e gectigi icin PDF belgesine bagli kaynaklarin kayitlari artik yalnizca pdfkit tablolarinda
yasar: `migrate()` once kopyalar (ve eski satirda sonradan yapilan yorum/renk degisikliklerini yansitir), sonra
kopyasi olusan eski satirlari SILER. Tekrar calistirmak guvenlidir (kopyasi olanlar yeniden eklenmez). PDF
belgesi olmayan kaynaklarin (HTML makaleler) kayitlari eski tablolarda kalir. Geri donus: gunluk veritabani
goruntusu (`utils.db_utils.snapshot_database_daily`) ve migration oncesi yedek.
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
class LegacyMigrationReport:
    copied: int  # pdfkit'e yeni kopyalanan
    updated: int  # kopyasi onceden var olup eski satirdan guncellenen
    removed: int  # kopyasi olusup eski tablodan silinen


def _timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    parsed = datetime.fromisoformat(str(value).replace(" ", "T"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class LegacyAnnotationImporter:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = AnnotationRepository(session)

    def _has_table(self, name: str) -> bool:
        """Eski tablo (ornegin `pdf_notes`) daraltma sonrasi yoksa ilgili adim atlanir."""
        return self._session.execute(
            text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :name"), {"name": name}
        ).first() is not None

    def migrate(self) -> LegacyMigrationReport:
        """Kopyala/guncelle, sonra kopyasi olan eski satirlari sil; tek islemde commit."""
        copied = updated = 0
        try:
            syncs = [self._sync_highlights, self._sync_terms] + ([self._sync_notes] if self._has_table("pdf_notes") else [])
            for sync in syncs:
                a, u = sync()
                copied, updated = copied + a, updated + u
            removed = self._delete_migrated_originals()
            self._drop_emptied_notes_table()
            self._session.commit()
        except Exception:
            self._session.rollback()
            log.exception("Eski PDF kayitlari pdfkit'e tasinamadi.")
            raise
        if copied or updated or removed:
            log.info("Eski PDF kayitlari pdfkit'e tasindi: +%d ~%d -%d", copied, updated, removed)
        return LegacyMigrationReport(copied, updated, removed)

    def _drop_emptied_notes_table(self) -> None:
        """Eski `pdf_notes` tablosu tamamen bosaldiysa kaldirir (Faz 8 daraltmasinin calisma zamani yarisi: migration
        tabloyu yalniz bossa siler; icinde satir olan veritabaninda tabloyu, son satir tasininca bu adim siler).
        Satir kaldiysa (belgesi henuz depoya alinmamis not) tablo korunur."""
        if self._has_table("pdf_notes") and self._session.execute(text("SELECT count(*) FROM pdf_notes")).scalar_one() == 0:
            self._session.execute(text("DROP TABLE pdf_notes"))

    def _delete_migrated_originals(self) -> int:
        removed = 0
        for table, ids in (
            ("highlights", self._repo.legacy_annotation_ids()),
            ("pdf_notes", self._repo.legacy_note_ids()),
            ("vocabulary", self._repo.legacy_term_ids()),
        ):
            if not self._has_table(table):
                continue
            for legacy_id in ids:
                removed += self._session.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": legacy_id}).rowcount
        return removed

    def _sync_highlights(self) -> tuple[int, int]:
        existing = self._repo.legacy_annotation_ids()
        added, updated = 0, 0
        for row in self._session.execute(_HIGHLIGHTS):
            legacy_id, document_id, content, page, color, start, length, comment, created = row
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
        return added, updated

    def _sync_notes(self) -> tuple[int, int]:
        existing = self._repo.legacy_note_ids()
        added, updated = 0, 0
        for legacy_id, document_id, page, x, y, note_text, created in self._session.execute(_NOTES):
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
        return added, updated

    def _sync_terms(self) -> tuple[int, int]:
        existing = self._repo.legacy_term_ids()
        added, updated = 0, 0
        for legacy_id, document_id, word, translation, sentence, mastery, created in self._session.execute(_TERMS):
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
        return added, updated
