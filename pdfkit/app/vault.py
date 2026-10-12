from sqlalchemy.orm import Session

from pdfkit.domain.citekey import base_citekey, make_unique
from pdfkit.domain.models import Document, SourceInfo
from pdfkit.infra.orm import PdfVaultNoteRow
from pdfkit.infra.vault_repository import VaultRepository


class CitekeyService:
    """Belge basina kalici citekey. Ilk atamada kaynak kunyesinden uretilir ve saklanir; sonradan kaynagin basligi ya da
    yazari duzelse de degismez (Obsidian baglantilari ve dosya adi kararli kalsin). commit/rollback bu katmandadir."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = VaultRepository(session)

    def get(self, document_id: int) -> str | None:
        row = self._repo.get(document_id)
        return row.citekey if row else None

    def ensure(self, document: Document, info: SourceInfo) -> str:
        existing = self._repo.get(document.id)
        if existing is not None:
            return existing.citekey
        base = base_citekey(info.authors, info.year, info.title or document.pdf_title or "", document.pdf_author)
        citekey = make_unique(base, self._repo.taken_citekeys())
        try:
            self._repo.add(PdfVaultNoteRow(document_id=document.id, citekey=citekey))
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return citekey
