"""Tam metin dizini sorgulari (FTS5). Yalnizca SQL; commit/rollback servistedir."""
from sqlalchemy import bindparam, select, text
from sqlalchemy.orm import Session

from pdfkit.infra.orm import PdfDocumentRow, PdfTextIndexRow
from pdfkit.infra.search_schema import FTS_TABLE, ROWID_SPAN, create_fts_table

STATUS_INDEXING = "indexing"
STATUS_OK = "ok"
STATUS_NO_TEXT = "no_text"
STATUS_FAILED = "failed"


def _rowid(document_id: int, page: int) -> int:
    return document_id * ROWID_SPAN + page


class PageIndexRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ---- sema ----
    def available(self) -> bool:
        """FTS5 tablosu var mi? (SQLite derlemesinde FTS5 yoksa migration tabloyu olusturamaz.)"""
        found = self._session.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"), {"name": FTS_TABLE}
        ).first()
        return found is not None

    def ensure_schema(self) -> bool:
        return create_fts_table(self._session)

    # ---- durum ----
    def state(self, document_id: int) -> PdfTextIndexRow | None:
        return self._session.get(PdfTextIndexRow, document_id)

    def set_state(self, document_id: int, status: str, page_count: int, version: int) -> None:
        row = self.state(document_id)
        if row is None:
            self._session.add(PdfTextIndexRow(document_id=document_id, status=status, page_count=page_count, version=version))
        else:
            row.status, row.page_count, row.version = status, page_count, version
        self._session.flush()

    def clear_state(self, document_id: int) -> None:
        row = self.state(document_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()

    def documents_needing_index(self, version: int) -> list[int]:
        """Metin katmani olan ve (hic dizinlenmemis | yarim kalmis | eski surumle dizinlenmis) belgeler."""
        rows = self._session.execute(
            select(PdfDocumentRow.id, PdfTextIndexRow.status, PdfTextIndexRow.version)
            .outerjoin(PdfTextIndexRow, PdfTextIndexRow.document_id == PdfDocumentRow.id)
            .where(PdfDocumentRow.has_text_layer.is_(True))
            .order_by(PdfDocumentRow.id)
        )
        pending = []
        for document_id, status, indexed_version in rows:
            if status is None or status == STATUS_INDEXING or indexed_version != version:
                pending.append(document_id)
        return pending

    def count_by_status(self) -> dict[str, int]:
        rows = self._session.execute(select(PdfTextIndexRow.status, text("count(*)")).group_by(PdfTextIndexRow.status))
        return {status: count for status, count in rows}

    # ---- sayfalar ----
    def delete_pages(self, document_id: int) -> None:
        self._session.execute(
            text(f"DELETE FROM {FTS_TABLE} WHERE rowid >= :lo AND rowid < :hi"),
            {"lo": _rowid(document_id, 0), "hi": _rowid(document_id + 1, 0)},
        )

    def add_pages(self, document_id: int, pages: list[tuple[int, str, str]]) -> None:
        """`pages`: (sayfa, katlanmis metin, ozgun metin)."""
        self._session.execute(
            text(f"INSERT INTO {FTS_TABLE}(rowid, folded, original) VALUES (:rowid, :folded, :original)"),
            [{"rowid": _rowid(document_id, page), "folded": folded, "original": original} for page, folded, original in pages],
        )

    def purge_orphans(self) -> int:
        """Durum satiri olmayan (belgesi silinmis) belgelerin sayfa satirlarini siler; silinen sayisi doner."""
        return self._session.execute(
            text(
                f"DELETE FROM {FTS_TABLE} WHERE rowid / :span NOT IN (SELECT document_id FROM pdf_text_index)"
            ),
            {"span": ROWID_SPAN},
        ).rowcount

    def page_row_count(self, document_id: int | None = None) -> int:
        if document_id is None:
            return self._session.execute(text(f"SELECT count(*) FROM {FTS_TABLE}")).scalar_one()
        return self._session.execute(
            text(f"SELECT count(*) FROM {FTS_TABLE} WHERE rowid >= :lo AND rowid < :hi"),
            {"lo": _rowid(document_id, 0), "hi": _rowid(document_id + 1, 0)},
        ).scalar_one()

    # ---- arama ----
    def resources_for(self, document_ids: list[int]) -> dict[int, tuple[int, str]]:
        """belge id -> (kaynak id, baslik); ayni belge birden cok kaynaktaysa en kucuk kaynak id'si."""
        if not document_ids:
            return {}
        # `resources` tablosu uygulamanindir (pdfkit modelini bilmez): ham SQL, `annotation_repository` ile ayni yol.
        rows = self._session.execute(
            text(
                "SELECT l.document_id, r.id, r.title FROM pdf_resource_documents l "
                "JOIN resources r ON r.id = l.resource_id WHERE l.document_id IN :ids ORDER BY r.id DESC"
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": document_ids},
        )
        return {document_id: (resource_id, title) for document_id, resource_id, title in rows}

    def query(self, match: str, limit: int) -> list[tuple[int, int, str, float]]:
        """(belge, sayfa, ozgun metin, bm25) uclulari, en alakali once. Yalniz `ok` belgeler."""
        rows = self._session.execute(
            text(
                f"SELECT {FTS_TABLE}.rowid, {FTS_TABLE}.original, bm25({FTS_TABLE}) AS rank "
                f"FROM {FTS_TABLE} "
                f"JOIN pdf_text_index i ON i.document_id = {FTS_TABLE}.rowid / :span AND i.status = :ok "
                f"WHERE {FTS_TABLE} MATCH :match ORDER BY rank LIMIT :limit"
            ),
            {"span": ROWID_SPAN, "ok": STATUS_OK, "match": match, "limit": limit},
        )
        return [(rowid // ROWID_SPAN, rowid % ROWID_SPAN, original, rank) for rowid, original, rank in rows]
