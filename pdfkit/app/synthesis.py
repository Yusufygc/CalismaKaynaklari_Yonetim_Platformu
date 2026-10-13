from sqlalchemy.orm import Session

from pdfkit.app.ports import ResourceCatalogPort
from pdfkit.domain.annotations import Annotation
from pdfkit.domain.models import SourceInfo
from pdfkit.domain.synthesis import Matrix, MatrixFilter, MatrixRow, build_row, make_matrix
from pdfkit.infra.annotation_repository import AnnotationRepository, annotation_from_row
from pdfkit.infra.repository import DocumentRepository
from pdfkit.infra.vault_repository import VaultRepository


class SynthesisService:
    """Kutuphane geneli literatur matrisi icin veri: butun PDF alintilari belge basina gruplu satirlar. Yalniz okur
    (commit yok). Veritabani okumalari toplu yapilir (alinti, belge, citekey birer sorgu); kunye `describe` ile gelir."""

    def __init__(self, session: Session, catalog: ResourceCatalogPort) -> None:
        self._annotations = AnnotationRepository(session)
        self._documents = DocumentRepository(session)
        self._vault = VaultRepository(session)
        self._catalog = catalog

    def rows(self) -> list[MatrixRow]:
        """Alintisi olan, en az bir kaynaga bagli her belge icin bir satir (suzgeçsiz)."""
        grouped: dict[int, list[Annotation]] = {}
        for row in self._annotations.all_annotation_rows():
            grouped.setdefault(row.document_id, []).append(annotation_from_row(row))
        owners = self._annotations.resources_by_document()  # belge -> [(kaynak, baslik)], kaynak kimligine gore sirali
        documents = self._documents.documents_by_ids(list(grouped))
        citekeys = self._vault.citekeys()
        rows = []
        for document_id, items in grouped.items():
            document, resources = documents.get(document_id), owners.get(document_id)
            if document is None or not resources:
                continue
            resource_id, title = resources[0]
            info = self._catalog.describe(resource_id) or SourceInfo(title or document.pdf_title or "")
            rows.append(build_row(document, info, citekeys.get(document_id), items, resource_id))
        return rows

    def matrix(self, matrix_filter: MatrixFilter | None = None) -> Matrix:
        return make_matrix(self.rows(), matrix_filter)
