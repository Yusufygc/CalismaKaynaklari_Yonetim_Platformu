from sqlalchemy import select
from sqlalchemy.orm import Session

from pdfkit.infra.orm import PdfVaultNoteRow


class VaultRepository:
    """Yalnizca sorgu/ekleme; commit/rollback servistedir."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, document_id: int) -> PdfVaultNoteRow | None:
        return self._session.get(PdfVaultNoteRow, document_id)

    def taken_citekeys(self) -> set[str]:
        return set(self._session.scalars(select(PdfVaultNoteRow.citekey)))

    def add(self, row: PdfVaultNoteRow) -> None:
        self._session.add(row)
        self._session.flush()
