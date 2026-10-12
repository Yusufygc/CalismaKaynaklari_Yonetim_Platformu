from PySide6.QtCore import Property, QObject, Signal, Slot

from pdfkit.domain.labels import LABELS
from pdfkit.ui.commands import AnnotationCommands
from pdfkit.ui.library import PdfLibrary
from pdfkit.ui.models import AnnotationListModel, NoteListModel
from pdfkit.ui.session import DocumentSession


class PdfBridge(QObject):
    """QML'in PDF okuyucu icin tek giris noktasi (`bridge.pdf`): belge acma/kapama, alinti/not modelleri ve
    yazma islemleri.

    `annotations` ve `notes` kalici tek modellerdir (belge degisince icerikleri yenilenir); sayfa katmanlari
    `pageModel(page)` / `notePageModel(page)` ile kendi sayfalarinin filtreli gorunumunu alir. Yazma
    islemleri modeli artimli gunceller; kullaniciya bildirim `notification` sinyaliyle gider."""

    currentDocumentChanged = Signal()
    termsChanged = Signal()
    notification = Signal(str, str)  # tur (info/error), mesaj
    contentChanged = Signal(int)  # kaynak kimligi: alinti/not/kelime degisti (havuz, cekmece, disa aktarim tazelenir)

    def __init__(self, library: PdfLibrary, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._model = AnnotationListModel(self)
        self._notes = NoteListModel(self)
        self._session = DocumentSession(library, self._model, self._notes, self)
        self._commands = AnnotationCommands(self._session, library, self.notification.emit)
        self._header: dict = {}

    # ------------------------------------------------------------------ #
    # Okuma
    # ------------------------------------------------------------------ #

    @Property(QObject, constant=True)
    def annotations(self) -> QObject:
        return self._model

    @Property(QObject, constant=True)
    def notes(self) -> QObject:
        return self._notes

    @Property(dict, notify=currentDocumentChanged)
    def currentDocument(self) -> dict:
        """Acik belgenin ozeti: {resourceId, documentId, fileUrl, pageCount, hasTextLayer}; kapaliysa {}."""
        return self._header

    @Property(list, notify=termsChanged)
    def terms(self) -> list:
        return [
            {
                "id": t.id, "uid": t.uid, "word": t.word, "translation": t.translation,
                "context": t.context_sentence or "", "page": t.segments[0].page if t.segments else -1,
                "mastery": t.mastery_level,
            }
            for t in self._session.terms
        ]

    @Property(list, constant=True)
    def labels(self) -> list:
        return [{"key": label.key, "name": label.name, "color": label.color} for label in LABELS]

    @Slot(int, result=bool)
    def openDocument(self, resource_id: int) -> bool:
        opened = self._session.open(resource_id)
        document = self._session.document
        self._set_header(
            {
                "resourceId": resource_id,
                "documentId": document.id,
                "fileUrl": self._library.file_path(document).as_uri(),
                "pageCount": document.page_count,
                "hasTextLayer": document.has_text_layer,
            }
            if opened and document
            else {}
        )
        self.termsChanged.emit()
        return opened

    @Slot()
    def closeDocument(self) -> None:
        self._session.close()
        self._set_header({})
        self.termsChanged.emit()

    @Slot(int, result=QObject)
    def pageModel(self, page: int) -> QObject:
        return self._session.page_model(page)

    @Slot(int, result=QObject)
    def notePageModel(self, page: int) -> QObject:
        return self._session.note_page_model(page)

    @Slot(int, result=int)
    def ensureGeometry(self, page: int) -> int:
        """Sayfa gorunur olunca cagrilir; eksik geometriyi dilimler halinde hesaplar. Ilk dilimde hesaplanan sayi doner."""
        return self._session.request_geometry(page)

    # ------------------------------------------------------------------ #
    # Alinti
    # ------------------------------------------------------------------ #

    @Slot("QVariantMap", str, result=int)
    def addHighlight(self, selection: dict, label_key: str) -> int:
        """Secili metni alinti olarak kaydeder. `selection`: {page, fromX, fromY, toX, toY} (sayfa noktasi uzayi).
        Ayni metin zaten alintiliysa yeni kayit olusturmaz, anlam etiketini gunceller. Alinti kimligi ya da 0."""
        return self._changed(self._commands.add_highlight(selection, label_key))

    @Slot(int, str, result=bool)
    def setLabel(self, annotation_id: int, label_key: str) -> bool:
        return self._changed(self._commands.set_label(annotation_id, label_key))

    @Slot(int, str, result=bool)
    def setComment(self, annotation_id: int, comment: str) -> bool:
        return self._changed(self._commands.set_comment(annotation_id, comment))

    @Slot(int, "QVariantList", result=bool)
    def setTags(self, annotation_id: int, tags: list) -> bool:
        return self._changed(self._commands.set_tags(annotation_id, [str(tag) for tag in tags]))

    @Slot(int, result=bool)
    def deleteAnnotation(self, annotation_id: int) -> bool:
        return self._changed(self._commands.delete(annotation_id))

    @Slot("QVariantList", result=int)
    def deleteAnnotations(self, annotation_ids: list) -> int:
        return self._changed(self._commands.delete_many([int(i) for i in annotation_ids]))

    # ------------------------------------------------------------------ #
    # Sayfa notu
    # ------------------------------------------------------------------ #

    @Slot(int, float, float, str, result=int)
    def addNote(self, page: int, x: float, y: float, text: str) -> int:
        return self._changed(self._commands.add_note(page, x, y, text))

    @Slot(int, str, result=bool)
    def updateNote(self, note_id: int, text: str) -> bool:
        return self._changed(self._commands.update_note(note_id, text))

    @Slot(int, result=bool)
    def deleteNote(self, note_id: int) -> bool:
        return self._changed(self._commands.delete_note(note_id))

    # ------------------------------------------------------------------ #
    # Kelime
    # ------------------------------------------------------------------ #

    @Slot("QVariantMap", str, result=int)
    def addTerm(self, selection: dict, translation: str) -> int:
        """Secili kelimeyi, gectigi cumleyle birlikte kelime havuzuna ekler. Kelime kimligi ya da 0."""
        term_id = self._commands.add_term(selection, translation)
        if term_id:
            self.termsChanged.emit()
        return self._changed(term_id)

    @Slot(int, result=bool)
    def deleteTerm(self, term_id: int) -> bool:
        deleted = self._commands.delete_term(term_id)
        if deleted:
            self.termsChanged.emit()
        return self._changed(deleted)

    # ------------------------------------------------------------------ #

    def _changed(self, result):
        """Basarili (sifir olmayan / True) yazma sonrasi `contentChanged` yayar; sonucu aynen dondurur."""
        if result and self._header:
            self.contentChanged.emit(self._header["resourceId"])
        return result

    def _set_header(self, header: dict) -> None:
        if header != self._header:
            self._header = header
            self.currentDocumentChanged.emit()
