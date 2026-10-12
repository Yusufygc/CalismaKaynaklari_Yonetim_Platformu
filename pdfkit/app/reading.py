import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from pdfkit.domain.errors import NotFoundError
from pdfkit.domain.reading import ACTIVE_GAP_SECONDS, MAX_ZOOM, MIN_ZOOM, ReadingState, progress_ratio
from pdfkit.infra.orm import PdfReadingStateRow
from pdfkit.infra.reading_repository import ReadingRepository, state_from_row
from pdfkit.infra.repository import DocumentRepository


def _finite(value: float, fallback: float) -> float:
    return value if math.isfinite(value) else fallback


class ReadingService:
    """Belge basina okuma durumu. commit/rollback bu katmandadir."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ReadingRepository(session)
        self._documents = DocumentRepository(session)

    def get(self, document_id: int) -> ReadingState | None:
        row = self._repo.get(document_id)
        return state_from_row(row) if row else None

    def save(
        self,
        document_id: int,
        page: int,
        loc_x: float,
        loc_y: float,
        zoom: float,
        *,
        seen_page: int | None = None,
        now: datetime | None = None,
    ) -> ReadingState:
        """Kalinan yeri yazar. `page` gorunumun ustundeki sayfadir (geri donus noktasi); `seen_page` kullanicinin
        gordugu (gorunumun ortasindaki) sayfadir ve ilerlemeyi belirler -- son sayfa gorunumun ustune hic gelmeyebilir.
        Sayfalar belgenin sinirlarina, yakinlastirma izinli araliga kirpilir; en uzak sayfa hic azalmaz. Aktif sure,
        onceki kayittan beri gecen sureye `ACTIVE_GAP_SECONDS` ust siniriyla eklenir."""
        document = self._documents.get_by_id(document_id)
        if document is None:
            raise NotFoundError(f"Belge bulunamadi: id={document_id}")
        now = now or datetime.now(timezone.utc)
        last = max(document.page_count - 1, 0)
        page = min(max(int(page), 0), last)
        seen = page if seen_page is None else min(max(int(seen_page), 0), last)
        zoom = min(max(_finite(zoom, 1.0), MIN_ZOOM), MAX_ZOOM)
        loc_x, loc_y = max(_finite(loc_x, 0.0), 0.0), max(_finite(loc_y, 0.0), 0.0)
        try:
            row = self._repo.get(document_id)
            if row is None:
                row = PdfReadingStateRow(
                    document_id=document_id, last_page=page, loc_x=loc_x, loc_y=loc_y, zoom=zoom,
                    max_page=max(page, seen), total_seconds=0, updated_at=now,
                )
                self._repo.add(row)
            else:
                row.total_seconds += self._active_seconds(row.updated_at, now)
                row.last_page, row.loc_x, row.loc_y, row.zoom = page, loc_x, loc_y, zoom
                row.max_page = max(row.max_page, page, seen)
                row.updated_at = now
            self._session.commit()
            return state_from_row(row)
        except Exception:
            self._session.rollback()
            raise

    def progress_map(self) -> dict[int, float]:
        """{kaynak kimligi: okunan oran}; yalnizca okuma durumu olan kaynaklar."""
        return {resource_id: progress_ratio(max_page, count) for resource_id, max_page, count in self._repo.progress_rows()}

    @staticmethod
    def _active_seconds(previous: datetime, now: datetime) -> int:
        if previous.tzinfo is None:  # SQLite zaman damgasini saat dilimsiz geri verir (UTC saklanir)
            previous = previous.replace(tzinfo=timezone.utc)
        gap = (now - previous).total_seconds()
        return int(min(max(gap, 0), ACTIVE_GAP_SECONDS))
