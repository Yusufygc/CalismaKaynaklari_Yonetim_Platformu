from sqlalchemy import select
from sqlalchemy.orm import Session

from pdfkit.domain.reading import ReadingState
from pdfkit.infra.orm import PdfDocumentRow, PdfReadingStateRow, PdfResourceLinkRow


def state_from_row(row: PdfReadingStateRow) -> ReadingState:
    return ReadingState(
        document_id=row.document_id,
        last_page=row.last_page,
        loc_x=row.loc_x,
        loc_y=row.loc_y,
        zoom=row.zoom,
        max_page=row.max_page,
        total_seconds=row.total_seconds,
    )


class ReadingRepository:
    """Yalnizca sorgu/ekleme; commit/rollback servistedir."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, document_id: int) -> PdfReadingStateRow | None:
        return self._session.get(PdfReadingStateRow, document_id)

    def add(self, row: PdfReadingStateRow) -> None:
        self._session.add(row)

    def progress_rows(self) -> list[tuple[int, int, int]]:
        """(kaynak kimligi, en uzak sayfa, sayfa sayisi) -- tek sorguyla tum kaynaklar (kart ilerlemesi)."""
        rows = self._session.execute(
            select(PdfResourceLinkRow.resource_id, PdfReadingStateRow.max_page, PdfDocumentRow.page_count)
            .join(PdfReadingStateRow, PdfReadingStateRow.document_id == PdfResourceLinkRow.document_id)
            .join(PdfDocumentRow, PdfDocumentRow.id == PdfResourceLinkRow.document_id)
        )
        return [(resource_id, max_page, page_count) for resource_id, max_page, page_count in rows]
