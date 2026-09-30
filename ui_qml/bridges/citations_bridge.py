from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from core.constants.strings import AppStrings
from services.citation_service import CitationService
from ui_qml.bridges.library_bridge import LibraryBridge
from ui_qml.bridges.reader_bridge import ReaderBridge
from ui_qml.context import BridgeContext
from ui_qml.serializers import annotate_library, serialize_paper
from utils.doi_utils import doi_from_url
from workers import PaperMetadataWorker, RelatedPapersWorker


def _empty_related_papers() -> dict:
    blank = {"loading": False, "error": "", "loaded": False, "items": []}
    return {"openalexId": "", "references": dict(blank), "citations": dict(blank)}


class CitationsBridge(QObject):
    """Okuyucudaki makalenin atif metni, OpenAlex akademik bilgisi ve referans / atif yapanlar listeleri."""

    relatedPapersChanged = Signal()

    def __init__(
        self, ctx: BridgeContext, library: LibraryBridge, reader: ReaderBridge, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._library = library
        self._reader = reader
        # Okuyucudaki makalenin referans / atif yapan listeleri (OpenAlex).
        self._related_papers: dict = _empty_related_papers()
        library.resourcesReloaded.connect(self._refresh_related_library_flags)

    @Property(dict, notify=relatedPapersChanged)
    def relatedPapers(self) -> dict:
        return self._related_papers

    # ------------------------------------------------------------------ #
    # Atif / akademik bilgi
    # ------------------------------------------------------------------ #

    @Slot(int, str, result=str)
    def citationText(self, resource_id: int, style: str) -> str:
        resource = self._ctx.controllers.resources.get_resource(resource_id)
        if resource is None:
            return ""
        try:
            return CitationService.format(resource.title, resource.extra_metadata or {}, style)
        except ValueError:
            return ""

    @Slot(int, str)
    def copyCitation(self, resource_id: int, style: str) -> None:
        text = self.citationText(resource_id, style)
        if not text:
            return
        QGuiApplication.clipboard().setText(text)
        self._ctx.notify.info(AppStrings.NOTIFICATION_CITATION_COPIED_FMT.format(style=style.upper()))

    @Slot(int)
    def fetchPaperMetadata(self, resource_id: int) -> None:
        """Kaynagin yazar/yil/dergi/DOI/OpenAlex bilgisini OpenAlex'ten getirip kaydeder."""
        resource = self._ctx.controllers.resources.get_resource(resource_id)
        if resource is None:
            return
        doi = (resource.extra_metadata or {}).get("doi") or doi_from_url(resource.url)
        worker = PaperMetadataWorker(resource_id, doi, None if doi else resource.title)
        worker.signals.finished.connect(self._on_paper_metadata_finished)
        self._ctx.thread_pool.start(worker)

    def _on_paper_metadata_finished(self, resource_id: int, paper, error: str) -> None:
        if error:
            self._ctx.notify.error(AppStrings.NOTIFICATION_PAPER_LOOKUP_FAILED)
            return
        if paper is None:
            self._ctx.notify.info(AppStrings.NOTIFICATION_PAPER_NOT_FOUND)
            return
        resources = self._ctx.controllers.resources
        resource = resources.get_resource(resource_id)
        if resource is None:
            return
        merged = {**(resource.extra_metadata or {}), **paper.to_metadata()}
        if resources.update_resource(resource_id, {"extra_metadata": merged}) is None:
            return
        self._library.reload()
        self._library.update_selected_if_matches(resource_id)
        self._reader.refresh_if_open(resource_id)
        self._ctx.notify.info(AppStrings.NOTIFICATION_PAPER_METADATA_SAVED)

    # ------------------------------------------------------------------ #
    # Referans / atif yapanlar (OpenAlex)
    # ------------------------------------------------------------------ #

    @Slot(int)
    def loadRelatedPapers(self, resource_id: int) -> None:
        """Okuyucudaki makalenin referanslarini ve ona atif yapanlari (OpenAlex) yukler."""
        resource = self._ctx.controllers.resources.get_resource(resource_id)
        openalex_id = ((resource.extra_metadata or {}).get("openalex_id") if resource else "") or ""
        self._related_papers = _empty_related_papers()
        self._related_papers["openalexId"] = openalex_id
        if openalex_id:
            for kind in ("references", "citations"):
                self._related_papers[kind]["loading"] = True
                worker = RelatedPapersWorker(openalex_id, kind)
                worker.signals.finished.connect(self._on_related_papers_finished)
                self._ctx.thread_pool.start(worker)
        self.relatedPapersChanged.emit()

    def _on_related_papers_finished(self, openalex_id: str, kind: str, papers, error: str) -> None:
        if openalex_id != self._related_papers.get("openalexId"):
            return  # Kullanici bu arada baska bir makaleye gecti.
        items = [serialize_paper(p) for p in papers]
        if items:
            annotate_library(items, self._ctx.library_index.get())
        self._related_papers[kind] = {
            "loading": False,
            "loaded": not error,
            "error": AppStrings.RELATED_PAPERS_LOAD_FAILED if error else "",
            "items": items,
        }
        self.relatedPapersChanged.emit()

    def _refresh_related_library_flags(self) -> None:
        """Kaynak eklenip silindikce Kaynakca sekmesindeki "Kutuphanede" durumunu tazeler."""
        items = [i for kind in ("references", "citations") for i in self._related_papers[kind]["items"]]
        if items and annotate_library(items, self._ctx.library_index.get()):
            self.relatedPapersChanged.emit()
