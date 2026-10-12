from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pdfkit.domain.models import Document
from pdfkit.infra.orm import PdfDocumentRow, PdfResourceLinkRow


def _to_domain(row: PdfDocumentRow) -> Document:
    return Document(
        id=row.id,
        sha256=row.sha256,
        rel_path=row.rel_path,
        byte_size=row.byte_size,
        page_count=row.page_count,
        has_text_layer=row.has_text_layer,
        pdf_title=row.pdf_title,
        pdf_author=row.pdf_author,
        doi=row.doi,
        source=row.source,
        original_filename=row.original_filename,
        imported_at=row.imported_at,
    )


class DocumentRepository:
    """Yalnizca sorgu/ekleme/silme yapar; commit/rollback servis katmanindadir."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, document_id: int) -> Document | None:
        row = self._session.get(PdfDocumentRow, document_id)
        return _to_domain(row) if row else None

    def get_by_sha(self, sha256: str) -> Document | None:
        row = self._session.scalar(select(PdfDocumentRow).where(PdfDocumentRow.sha256 == sha256))
        return _to_domain(row) if row else None

    def get_for_resource(self, resource_id: int) -> Document | None:
        row = self._session.scalar(
            select(PdfDocumentRow)
            .join(PdfResourceLinkRow, PdfResourceLinkRow.document_id == PdfDocumentRow.id)
            .where(PdfResourceLinkRow.resource_id == resource_id)
        )
        return _to_domain(row) if row else None

    def resource_ids_for(self, document_id: int) -> list[int]:
        return list(
            self._session.scalars(
                select(PdfResourceLinkRow.resource_id).where(PdfResourceLinkRow.document_id == document_id)
            )
        )

    def add(self, row: PdfDocumentRow) -> Document:
        self._session.add(row)
        self._session.flush()
        return _to_domain(row)

    def link(self, resource_id: int, document_id: int) -> None:
        link = self._session.get(PdfResourceLinkRow, resource_id)
        if link is None:
            self._session.add(PdfResourceLinkRow(resource_id=resource_id, document_id=document_id))
        else:
            link.document_id = document_id
        self._session.flush()

    def linked_document_ids(self) -> list[int]:
        """En az bir kaynaga bagli belgelerin kimlikleri (artan sirayla)."""
        return sorted(set(self._session.scalars(select(PdfResourceLinkRow.document_id))))

    def linked_resource_ids(self) -> set[int]:
        return set(self._session.scalars(select(PdfResourceLinkRow.resource_id)))

    def unlinked_documents(self) -> list[Document]:
        linked = select(PdfResourceLinkRow.document_id)
        rows = self._session.scalars(select(PdfDocumentRow).where(PdfDocumentRow.id.not_in(linked)))
        return [_to_domain(row) for row in rows]

    def known_rel_paths(self) -> set[str]:
        return set(self._session.scalars(select(PdfDocumentRow.rel_path)))

    def delete_document(self, document_id: int) -> None:
        self._session.execute(delete(PdfDocumentRow).where(PdfDocumentRow.id == document_id))
        self._session.flush()
