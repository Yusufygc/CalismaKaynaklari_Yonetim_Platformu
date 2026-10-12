from PySide6.QtCore import Property, QCoreApplication, QObject, QTimer, Signal, Slot

from core.logger import log

from pdfkit.domain.annotations import STATUS_ORPHANED
from pdfkit.domain.labels import LABELS, effective_color, name_for_label
from pdfkit.ui.commands import AnnotationCommands
from pdfkit.ui.library import PdfLibrary
from pdfkit.ui.models import AnnotationListModel, NoteListModel
from pdfkit.ui.session import DocumentSession


_READING_SAVE_DELAY_MS = 1000


class PdfBridge(QObject):
    """QML'in PDF okuyucu icin tek giris noktasi (`bridge.pdf`): belge acma/kapama, alinti/not modelleri ve
    yazma islemleri.

    `annotations` ve `notes` kalici tek modellerdir (belge degisince icerikleri yenilenir); sayfa katmanlari
    `pageModel(page)` / `notePageModel(page)` ile kendi sayfalarinin filtreli gorunumunu alir. Yazma
    islemleri modeli artimli gunceller; kullaniciya bildirim `notification` sinyaliyle gider."""

    currentDocumentChanged = Signal()
    revisionChanged = Signal()
    termsChanged = Signal()
    notification = Signal(str, str)  # tur (info/error), mesaj
    readingStateChanged = Signal()
    readingProgressChanged = Signal(int)  # kaynak kimligi: okuma durumu yazildi (kart ilerlemesi tazelenir)
    contentChanged = Signal(int)  # kaynak kimligi: alinti/not/kelime degisti (havuz, cekmece, disa aktarim tazelenir)

    def __init__(self, library: PdfLibrary, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._model = AnnotationListModel(self)
        self._notes = NoteListModel(self)
        self._session = DocumentSession(library, self._model, self._notes, self)
        self._commands = AnnotationCommands(self._session, library, self.notification.emit)
        self._header: dict = {}
        self._revision = 0
        self._reading_state: dict = {}
        self._pending_reading: tuple | None = None  # (belge, sayfa, x, y, zoom, gorulen sayfa): gecikmeli yazilmayi bekler
        self._reading_timer = QTimer(self)
        self._reading_timer.setSingleShot(True)
        self._reading_timer.setInterval(_READING_SAVE_DELAY_MS)
        self._reading_timer.timeout.connect(self._flush_reading_state)
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._flush_reading_state)  # uygulama kapanirken son konum kaybolmasin

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

    @Property(dict, notify=readingStateChanged)
    def readingState(self) -> dict:
        """Belge acilirken okuma durumu: {hasState, page, x, y, zoom}; kayit yoksa hasState=False."""
        return self._reading_state

    @Property(int, notify=revisionChanged)
    def revision(self) -> int:
        """Belge acilip kapaninca ve her basarili yazmadan sonra artar; `notebookItems` gibi turetilmis
        listelerin QML baglamalarini yeniden degerlendirmek icin kullanilir."""
        return self._revision

    @Property(int, notify=revisionChanged)
    def orphanCount(self) -> int:
        """Acik belgede konumu bulunamayan (yetim) alinti sayisi."""
        return self._model.count_with_status(STATUS_ORPHANED)

    @Property(list, notify=revisionChanged)
    def tags(self) -> list:
        """Acik belgedeki serbest alinti etiketleri: [{name, count}], cok kullanilandan aza."""
        return [{"name": name, "count": count} for name, count in self._model.tag_counts()]

    @Slot(str, str, bool, int, result="QVariantList")
    def notebookItems(self, label_key: str, tag: str, only_orphaned: bool, _revision: int = 0) -> list:
        """Yan paneldeki 'Notlarim' listesi: alintilar (istenirse tek anlam etiketine, serbest etikete ya da yalniz
        yetim olanlara gore suzulur) ve sayfa notlari, sayfa/konum sirali. Suzgec varken sayfa notlari gizlenir.
        `_revision` kullanilmaz; QML baglamasinin `revision` degisince yeniden calismasi icin gecilir."""
        items = []
        for annotation, rect in self._model.rows_with_rect():
            if label_key and annotation.label_key != label_key:
                continue
            if tag and tag not in annotation.tags:
                continue
            if only_orphaned and annotation.status != STATUS_ORPHANED:
                continue
            items.append(
                {
                    "kind": "highlight", "id": annotation.id, "page": annotation.page if annotation.page is not None else -1,
                    "color": effective_color(annotation.label_key, annotation.color),
                    "label": name_for_label(annotation.label_key), "text": annotation.quote_exact,
                    "comment": annotation.comment or "", "status": annotation.status, "tags": annotation.tags,
                    "x": rect[0] if rect else -1, "y": rect[1] if rect else -1,
                }
            )
        if not (label_key or tag or only_orphaned):
            items += [
                {"kind": "note", "id": n.id, "page": n.page, "color": "", "label": "Not", "text": n.text,
                 "comment": "", "status": "ok", "tags": [], "x": n.x, "y": n.y}
                for n in self._notes.all_notes()
            ]
        items.sort(key=lambda item: (item["page"], item["y"]))
        return items

    @Property(list, constant=True)
    def labels(self) -> list:
        return [{"key": label.key, "name": label.name, "color": label.color} for label in LABELS]

    @Slot(int, result=bool)
    def openDocument(self, resource_id: int) -> bool:
        self._flush_reading_state()
        opened = self._session.open(resource_id)
        document = self._session.document
        self._load_reading_state(document.id if opened and document else None)
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
        self._bump_revision()
        return opened

    @Slot()
    def closeDocument(self) -> None:
        self._flush_reading_state()
        self._session.close()
        self._load_reading_state(None)
        self._set_header({})
        self.termsChanged.emit()
        self._bump_revision()

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
    # Okuma durumu
    # ------------------------------------------------------------------ #

    @Slot(int, float, float, float, int)
    def saveReadingState(self, page: int, x: float, y: float, zoom: float, seen_page: int) -> None:
        """Kalinan yeri kaydeder: gorunumun ustundeki sayfa + sayfa ici konum + yakinlastirma; `seen_page` ilerleme
        icin gorunumun ortasindaki sayfa. Sik cagrilir; yazma 1 sn birlestirilir, belge kapanirken anında yazilir."""
        document = self._session.document
        if document is None:
            return
        self._pending_reading = (document.id, page, x, y, zoom, seen_page)
        if not self._reading_timer.isActive():
            self._reading_timer.start()

    def _flush_reading_state(self) -> None:
        self._reading_timer.stop()
        pending, self._pending_reading = self._pending_reading, None
        if pending is None or not self._header:
            return
        document_id, page, x, y, zoom, seen_page = pending
        try:
            self._library.reading().save(document_id, page, x, y, zoom, seen_page=seen_page)
        except Exception:
            log.exception("Okuma durumu kaydedilemedi: belge=%s", document_id)
            return
        self.readingProgressChanged.emit(self._header["resourceId"])

    def _load_reading_state(self, document_id: int | None) -> None:
        state = self._library.reading().get(document_id) if document_id is not None else None
        self._reading_state = (
            {"hasState": True, "page": state.last_page, "x": state.loc_x, "y": state.loc_y, "zoom": state.zoom}
            if state
            else {"hasState": False, "page": 0, "x": 0.0, "y": 0.0, "zoom": 0.0}
        )
        self.readingStateChanged.emit()

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

    @Slot(int, "QVariantMap", result=bool)
    def relinkAnnotation(self, annotation_id: int, selection: dict) -> bool:
        """Yetim alintiyi sayfada yeni secilen metne baglar (`selection` addHighlight ile ayni harita)."""
        return self._changed(self._commands.relink(annotation_id, selection))

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
            self._bump_revision()
            self.contentChanged.emit(self._header["resourceId"])
        return result

    def _bump_revision(self) -> None:
        self._revision += 1
        self.revisionChanged.emit()

    def _set_header(self, header: dict) -> None:
        if header != self._header:
            self._header = header
            self.currentDocumentChanged.emit()
