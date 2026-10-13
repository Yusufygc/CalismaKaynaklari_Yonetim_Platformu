import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from core.logger import log
from pdfkit.domain.models import Document, PreparedPdf
from pdfkit.infra.file_store import FileStore
from pdfkit.infra.orm import PdfDocumentRow
from pdfkit.infra.repository import DocumentRepository


@dataclass(frozen=True)
class GcReport:
    collected: int  # karantinaya alinan baglantisiz belge + sahipsiz dosya sayisi
    pending: int  # tasinamayan (kilitli) belge sayisi; sonra yeniden denenmeli


_STRAY_GRACE_SECONDS = 3600  # Yeni yazilan dosya kaydi henuz eklenmeden "sahipsiz" sayilmasin.


class DocumentService:
    """Belge kayitlari ve kaynak baglantilari. commit/rollback bu katmandadir (projenin oturum kurali)."""

    def __init__(self, session: Session, store: FileStore) -> None:
        self._session = session
        self._store = store
        self._repo = DocumentRepository(session)

    @property
    def store(self) -> FileStore:
        return self._store

    def get(self, document_id: int) -> Document | None:
        return self._repo.get_by_id(document_id)

    def find_by_sha(self, sha256: str) -> Document | None:
        return self._repo.get_by_sha(sha256)

    def find_by_sha_prefix(self, prefix: str) -> Document | None:
        """Derin baglantidaki kisaltilmis SHA-256 ile belge; yok ya da belirsizse (birden cok eslesme) None."""
        found = self._repo.find_by_sha_prefix(prefix)
        return found[0] if len(found) == 1 else None

    def document_for_resource(self, resource_id: int) -> Document | None:
        return self._repo.get_for_resource(resource_id)

    def resources_with_document(self, document_id: int) -> list[int]:
        return self._repo.resource_ids_for(document_id)

    def linked_resource_ids(self) -> set[int]:
        return self._repo.linked_resource_ids()

    def register(self, prepared: PreparedPdf, resource_id: int, source: str) -> Document:
        """Hazirlanan PDF'i belge olarak kaydeder (ayni SHA-256 varsa mevcut belge) ve kaynaga baglar."""
        try:
            document = self._repo.get_by_sha(prepared.stored.sha256)
            if document is None:
                inspection = prepared.inspection
                document = self._repo.add(
                    PdfDocumentRow(
                        sha256=prepared.stored.sha256,
                        rel_path=prepared.stored.rel_path,
                        byte_size=prepared.stored.byte_size,
                        page_count=inspection.page_count,
                        has_text_layer=inspection.has_text_layer,
                        pdf_title=inspection.title,
                        pdf_author=inspection.author,
                        doi=inspection.doi,
                        source=source,
                        original_filename=prepared.original_filename,
                    )
                )
            self._repo.link(resource_id, document.id)
            self._session.commit()
            return document
        except Exception:
            self._session.rollback()
            log.exception("PDF belgesi kaydedilemedi: sha=%s", prepared.stored.sha256[:8])
            raise

    def collect_garbage(self) -> GcReport:
        """Hicbir kaynaga bagli olmayan belgelerin dosyasini karantinaya alir ve satirini siler; ayrica
        veritabaninda kaydi olmayan (kayit asamasinda hata almis) depo dosyalarini da karantinaya alir.
        Dosya tasinamazsa (Windows kilidi) satir korunur ve `pending` olarak bildirilir."""
        collected = pending = 0
        for document in self._repo.unlinked_documents():
            if not self._store.quarantine(document.rel_path):
                pending += 1
                continue
            self._repo.delete_document(document.id)
            collected += 1
        if collected:
            self._session.commit()
        collected += self._quarantine_strays()
        if collected:
            log.info("Baglantisiz %d PDF dosyasi karantinaya alindi.", collected)
        self._store.purge_trash()
        return GcReport(collected=collected, pending=pending)

    def _quarantine_strays(self) -> int:
        known = self._repo.known_rel_paths()
        cutoff = time.time() - _STRAY_GRACE_SECONDS
        moved = 0
        for rel_path, modified in self._store.stored_files():
            if rel_path not in known and modified < cutoff and self._store.quarantine(rel_path):
                moved += 1
        return moved
