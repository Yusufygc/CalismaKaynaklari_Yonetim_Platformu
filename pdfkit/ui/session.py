from collections import OrderedDict
from dataclasses import replace
from functools import partial

from PySide6.QtCore import QObject, QPointF, QTimer
from PySide6.QtPdf import QPdfDocument, QPdfSelection

from core.logger import log
from pdfkit.domain.annotations import STATUS_OK, STATUS_PENDING, Segment
from pdfkit.domain.annotations import Term
from pdfkit.domain.models import Document
from pdfkit.domain.text import sanitize_text
from pdfkit.ui.library import PdfLibrary
from pdfkit.ui.models import AnnotationListModel, NoteListModel, PageFilterModel
from pdfkit.ui.pdf_text import QtPageTextProvider, current_engine_fp


MAX_PAGE_MODELS = 64  # Sayfa filtreleri her kaynak degisiminde degerlendirilir; kullanilmayanlar atilir.
GEOMETRY_CHUNK = 8  # Tek seferde hesaplanan alinti sayisi (~5 ms/alinti): her dilim bir kareyi bloklamaz.


class DocumentSession(QObject):
    """Acik belge: QPdfDocument + alinti modeli. Belge acilirken bekleyen eski kayitlarin baglamini tamamlar,
    geometriyi yalnizca gorunen sayfalar icin tembel hesaplayip kalici yazar (belge basina bir kez).

    Qt nesneleri yalnizca UI thread'inde kullanilir."""

    def __init__(
        self,
        library: PdfLibrary,
        model: AnnotationListModel,
        notes_model: NoteListModel | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._library = library
        self._model = model
        self._notes_model = notes_model if notes_model is not None else NoteListModel(self)
        self._terms: list[Term] = []
        self._document: Document | None = None
        self._qdoc: QPdfDocument | None = None
        self._provider: QtPageTextProvider | None = None
        self._page_models: OrderedDict[int, PageFilterModel] = OrderedDict()
        self._note_page_models: OrderedDict[int, PageFilterModel] = OrderedDict()
        self._geometry_failed: set[int] = set()
        self._generation = 0  # open/close ile artar; eski belgenin bekleyen dilimleri kendini iptal eder

    @property
    def document(self) -> Document | None:
        return self._document

    @property
    def is_open(self) -> bool:
        return self._document is not None

    @property
    def qdoc(self) -> QPdfDocument | None:
        return self._qdoc

    @property
    def provider(self) -> QtPageTextProvider | None:
        return self._provider

    @property
    def annotations_model(self) -> AnnotationListModel:
        return self._model

    @property
    def notes_model(self) -> NoteListModel:
        return self._notes_model

    @property
    def terms(self) -> list[Term]:
        return self._terms

    def reload_terms(self) -> None:
        self._terms = self._library.annotations().list_terms(self._document.id) if self._document else []

    def open(self, resource_id: int) -> bool:
        """Kaynagin PDF belgesini acar ve alintilarini modele yukler. Belge yoksa/acilamazsa False."""
        self.close()
        self._generation += 1
        document = self._library.documents().document_for_resource(resource_id)
        if document is None:
            return False
        qdoc = QPdfDocument()
        qdoc.load(str(self._library.file_path(document)))
        if qdoc.status() != QPdfDocument.Status.Ready:
            log.warning("Belge acilamadi: %s", document.rel_path)
            qdoc.deleteLater()
            return False
        self._document, self._qdoc = document, qdoc
        self._provider = QtPageTextProvider(qdoc)
        service = self._library.annotations()
        items = service.list_highlights(document.id)
        if any(a.status == STATUS_PENDING for a in items):
            service.backfill_context(document.id, self._provider, current_engine_fp())
            items = service.list_highlights(document.id)
        self._model.set_annotations(items)
        self._notes_model.set_notes(service.list_notes(document.id))
        self.reload_terms()
        return True

    def close(self) -> None:
        self._generation += 1
        self._geometry_failed.clear()
        self._model.clear()
        self._notes_model.clear()
        self._terms = []
        if self._qdoc is not None:
            # Windows'ta QPdfDocument dosyayi kilitler: close() + deleteLater() (zorla flush guvenli degil).
            self._qdoc.close()
            self._qdoc.deleteLater()
        self._document = self._qdoc = self._provider = None

    def page_model(self, page: int) -> PageFilterModel:
        return self._cached_page_model(self._page_models, self._model, self, page)

    @staticmethod
    def _cached_page_model(
        cache: "OrderedDict[int, PageFilterModel]", source, owner: QObject, page: int
    ) -> PageFilterModel:
        """Sayfa filtreleri kalici kaynak modele bagli oldugundan belge degisiminde de gecerlidir; LRU ile
        sinirlanir (atilan filtre `deleteLater` ile silinir, QML tarafindaki referans bosalir)."""
        model = cache.get(page)
        if model is not None:
            cache.move_to_end(page)
            return model
        model = PageFilterModel(source, page, owner)  # ebeveyni olan nesneyi QML'in GC'si silmez
        cache[page] = model
        if len(cache) > MAX_PAGE_MODELS:
            _evicted_page, evicted = cache.popitem(last=False)
            evicted.deleteLater()
        return model

    def note_page_model(self, page: int) -> PageFilterModel:
        return self._cached_page_model(self._note_page_models, self._notes_model, self, page)

    def resolve_selection(self, selection: dict) -> tuple[int, QPdfSelection] | None:
        """QML'in gonderdigi secim haritasini ({page, fromX, fromY, toX, toY}; sayfa noktasi uzayinda) Qt
        secimine cevirir. Gecersiz ya da yalnizca bosluk iceren secimde None."""
        if self._qdoc is None:
            return None
        page = int(selection["page"])
        found = self._qdoc.getSelection(
            page, QPointF(selection["fromX"], selection["fromY"]), QPointF(selection["toX"], selection["toY"])
        )
        if not found.isValid() or not sanitize_text(found.text()).strip():
            return None
        return page, found

    def request_geometry(self, page: int) -> int:
        """Sayfa gorunur olunca cagrilir: ilk dilimi hemen hesaplar (hesaplanan sayiyi dondurur), kalanlari
        olay dongusu turlarina yayar; boylece eski kayitlarin ilk acilisi tek bir uzun donma olmaz."""
        done = self.ensure_geometry(page, limit=GEOMETRY_CHUNK)
        if done and self._pending_geometry(page):
            QTimer.singleShot(0, partial(self._continue_geometry, page, self._generation))
        return done

    def _continue_geometry(self, page: int, generation: int) -> None:
        if generation != self._generation:
            return
        if self.ensure_geometry(page, limit=GEOMETRY_CHUNK) and self._pending_geometry(page):
            QTimer.singleShot(0, partial(self._continue_geometry, page, generation))

    def _pending_geometry(self, page: int) -> int:
        fingerprint = current_engine_fp()
        return sum(
            1
            for a in self._model.annotations_on_page(page)
            if a.status == STATUS_OK and a.id not in self._geometry_failed and _needs_geometry(a, fingerprint)
        )

    def ensure_geometry(self, page: int, limit: int | None = None) -> int:
        """`page` sayfasindaki, poligonu olmayan ya da baska motor surumunden kalma alintilarin geometrisini
        hesaplar (en cok `limit` tane) ve kalici yazar. Guncellenen alinti sayisini dondurur."""
        if self._qdoc is None or self._document is None:
            return 0
        fingerprint = current_engine_fp()
        updates = {}
        for annotation in self._model.annotations_on_page(page):
            if limit is not None and len(updates) >= limit:
                break
            if annotation.id in self._geometry_failed or annotation.status != STATUS_OK:
                continue
            if not _needs_geometry(annotation, fingerprint):
                continue
            segments = [self._with_geometry(segment) for segment in annotation.segments]
            if any(s.polygons for s in segments):
                updates[annotation.id] = segments
            else:
                self._geometry_failed.add(annotation.id)  # Qt secimi gecersiz saydi: dongude tekrar denenmesin
        if not updates:
            return 0
        for stored in self._library.annotations().store_geometry(updates, fingerprint):
            self._model.upsert(stored)
        return len(updates)

    def _with_geometry(self, segment: Segment) -> Segment:
        selection = self._qdoc.getSelectionAtIndex(segment.page, segment.start, segment.end - segment.start)
        if not selection.isValid():
            return segment
        polygons = [[(p.x(), p.y()) for p in polygon] for polygon in selection.bounds()]
        return replace(segment, polygons=polygons or None)


def _needs_geometry(annotation, fingerprint: str) -> bool:
    return annotation.engine_fp != fingerprint or any(not s.polygons for s in annotation.segments)
