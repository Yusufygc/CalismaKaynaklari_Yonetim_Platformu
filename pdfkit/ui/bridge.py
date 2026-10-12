from PySide6.QtCore import Property, QObject, Signal, Slot

from pdfkit.domain.labels import LABELS
from pdfkit.ui.library import PdfLibrary
from pdfkit.ui.models import AnnotationListModel
from pdfkit.ui.session import DocumentSession


class PdfBridge(QObject):
    """QML'in PDF okuyucu icin tek giris noktasi (`bridge.pdf`): belge acma/kapama, alinti modelleri.

    `annotations` kalici tek modeldir (belge degisince icerigi yenilenir); sayfa katmanlari
    `pageModel(page)` ile kendi sayfalarinin filtreli gorunumunu alir."""

    currentDocumentChanged = Signal()

    def __init__(self, library: PdfLibrary, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._model = AnnotationListModel(self)
        self._session = DocumentSession(library, self._model, self)
        self._header: dict = {}

    @Property(QObject, constant=True)
    def annotations(self) -> QObject:
        return self._model

    @Property(dict, notify=currentDocumentChanged)
    def currentDocument(self) -> dict:
        """Acik belgenin ozeti: {resourceId, documentId, fileUrl, pageCount, hasTextLayer}; kapaliysa {}."""
        return self._header

    @Property(list, constant=True)
    def labels(self) -> list:
        return [{"key": label.key, "name": label.name, "color": label.color} for label in LABELS]

    @Slot(int, result=bool)
    def openDocument(self, resource_id: int) -> bool:
        if not self._session.open(resource_id):
            self._set_header({})
            return False
        document = self._session.document
        self._set_header(
            {
                "resourceId": resource_id,
                "documentId": document.id,
                "fileUrl": self._library.file_path(document).as_uri(),
                "pageCount": document.page_count,
                "hasTextLayer": document.has_text_layer,
            }
        )
        return True

    @Slot()
    def closeDocument(self) -> None:
        self._session.close()
        self._set_header({})

    @Slot(int, result=QObject)
    def pageModel(self, page: int) -> QObject:
        return self._session.page_model(page)

    @Slot(int, result=int)
    def ensureGeometry(self, page: int) -> int:
        """Sayfa gorunur olunca cagrilir; eksik geometriyi dilimler halinde hesaplar. Ilk dilimde hesaplanan sayi doner."""
        return self._session.request_geometry(page)

    def _set_header(self, header: dict) -> None:
        if header != self._header:
            self._header = header
            self.currentDocumentChanged.emit()
