from sqlalchemy.orm import Session

from pdfkit.app.annotations import AnnotationService
from pdfkit.app.ports import ResourceCatalogPort
from pdfkit.domain.citekey import base_citekey, make_unique
from pdfkit.domain.models import Document, SourceInfo
from pdfkit.domain.vault_note import NoteContent
from pdfkit.infra.orm import PdfVaultNoteRow
from pdfkit.infra.repository import DocumentRepository
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


class NoteBuilder:
    """Bir belgenin vault notu icin gereken her seyi (belge, kaynak kunyesi, citekey, alinti/not/kelimeler) toplar.
    Veritabani okumalari ve citekey atamasi icindir: ana thread'de calisir; sonuc (salt okunur veri) worker'a gider."""

    def __init__(self, session: Session, catalog: ResourceCatalogPort) -> None:
        self._documents = DocumentRepository(session)
        self._annotations = AnnotationService(session)
        self._citekeys = CitekeyService(session)
        self._catalog = catalog

    def linked_document_ids(self) -> list[int]:
        return self._documents.linked_document_ids()

    def document_id_for_resource(self, resource_id: int) -> int | None:
        document = self._documents.get_for_resource(resource_id)
        return document.id if document else None

    def build(self, document_id: int) -> NoteContent | None:
        """Belgenin not icerigi; belge ya da bagli kaynak yoksa None (yazilacak bir sey yok)."""
        document = self._documents.get_by_id(document_id)
        resource_ids = self._documents.resource_ids_for(document_id) if document else []
        if document is None or not resource_ids:
            return None
        info = self._catalog.describe(min(resource_ids)) or SourceInfo(
            title=document.pdf_title or document.original_filename or "", doi=document.doi
        )
        return NoteContent(
            document=document,
            info=info,
            citekey=self._citekeys.ensure(document, info),
            annotations=self._annotations.list_highlights(document_id),
            notes=self._annotations.list_notes(document_id),
            terms=self._annotations.list_terms(document_id),
        )
