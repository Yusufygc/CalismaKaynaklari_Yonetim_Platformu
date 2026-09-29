from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication

from core.constants.highlight_labels import HIGHLIGHT_LABELS
from core.constants.strings import AppStrings
from core.events import event_bus
from services.citation_service import CitationService
from services.export_service import ExportService
from services.pdf_download_service import looks_like_remote_pdf
from services.schemas import HighlightPosition
from ui_qml.bridges.library_bridge import LibraryBridge
from ui_qml.context import BridgeContext
from ui_qml.file_export import write_export
from ui_qml.serializers import (
    DEFAULT_HIGHLIGHT_COLOR, annotate_library, serialize_paper, serialize_pool_highlight, serialize_pool_vocabulary,
)
from utils.doi_utils import doi_from_url
from utils.text_utils import extract_sentence, sanitize_utf8
from workers import PaperMetadataWorker, PdfOutlineWorker, RelatedPapersWorker


class ReaderBridge(QObject):
    """Okuyucu: HTML/PDF okuma, alinti-kelime-not, PDF anahati, atif, OpenAlex bilgisi (referans/atif
    listeleri) ve Markdown disa aktarimi."""

    currentReaderResourceChanged = Signal()
    highlightsChanged = Signal()
    vocabularyChanged = Signal()
    relatedPapersChanged = Signal()
    pdfOutlinesChanged = Signal()
    readerArticleUpdated = Signal(int, str)

    def __init__(
        self,
        ctx: BridgeContext,
        library: LibraryBridge,
        navigate: Callable[[str], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._library = library
        self._navigate = navigate  # Kok bridge'in `setCurrentView`'i: hangi sayfanin gorunecegi orada tutulur.
        self._current: dict = {}
        self._highlights_cache: list[dict] = []
        self._vocabulary_cache: list[dict] = []
        # Okuyucudaki makalenin referans / atif yapan listeleri (OpenAlex).
        self._related_papers: dict = self._empty_related_papers()
        # PDF anahatlari (dosya URL'si -> liste) arka planda okunur; yuklenirken anahtar yoktur.
        self._pdf_outlines: dict[str, list] = {}
        self._pdf_outlines_loading: set[str] = set()

        ctx.pdf_files.downloadFinished.connect(self._on_pdf_download_finished)
        ctx.pdf_files.documentReleased.connect(self._on_document_released)
        ctx.extractor.extracted.connect(self._on_full_text_extracted)
        library.resourcesReloaded.connect(self._refresh_related_library_flags)
        event_bus.highlight_added.connect(self._on_highlights_event)
        event_bus.highlight_deleted.connect(self._on_highlights_event)
        event_bus.vocabulary_added.connect(self._on_vocabulary_event)
        event_bus.vocabulary_deleted.connect(self._on_vocabulary_event)
        event_bus.resource_deleted.connect(self._on_resource_deleted)
        for signal in (event_bus.category_updated, event_bus.category_deleted,
                       event_bus.tag_updated, event_bus.tag_deleted):
            signal.connect(self._on_taxonomy_changed)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @Property(dict, notify=currentReaderResourceChanged)
    def currentReaderResource(self) -> dict:
        return self._current

    @Property(list, notify=highlightsChanged)
    def highlights(self) -> list:
        return self._highlights_cache

    @Property(list, notify=vocabularyChanged)
    def vocabulary(self) -> list:
        return self._vocabulary_cache

    @Property(list, constant=True)
    def highlightLabels(self) -> list:
        return HIGHLIGHT_LABELS

    @Property(dict, notify=relatedPapersChanged)
    def relatedPapers(self) -> dict:
        return self._related_papers

    @Property(dict, notify=pdfOutlinesChanged)
    def pdfOutlines(self) -> dict:
        """Yuklenmis PDF anahatlari: {dosya URL'si: [{title, level, page}]}; yuklenmemisse anahtar yoktur."""
        return self._pdf_outlines

    # ------------------------------------------------------------------ #
    # Yukleme / olaylar
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        self.reload_highlights()
        self.reload_vocabulary()

    def reload_highlights(self) -> None:
        self._highlights_cache = [
            serialize_pool_highlight(h) for h in self._ctx.controllers.highlights.load_all_highlights()
        ]
        self.highlightsChanged.emit()

    def reload_vocabulary(self) -> None:
        self._vocabulary_cache = [
            serialize_pool_vocabulary(v) for v in self._ctx.controllers.vocabulary.load_all_vocabulary()
        ]
        self.vocabularyChanged.emit()

    def _on_highlights_event(self, _id: int) -> None:
        self.reload_highlights()

    def _on_vocabulary_event(self, _id: int) -> None:
        self.reload_vocabulary()

    def _on_resource_deleted(self, resource_id: int) -> None:
        if self._current.get("id") == resource_id:
            self.closeReader()

    def _on_taxonomy_changed(self, _id: int) -> None:
        """Kategori/etiket adi ya da rengi degisince acik okuyucu eski adi gostermesin."""
        self.refresh_current()

    def refresh_current(self, resource_id: int | None = None) -> None:
        """Acik okuyucu kaynagini (varsa) yeniden serilestirir. `resource_id` verilirse o kaynak icin."""
        target_id = resource_id if resource_id is not None else self._current.get("id")
        if not target_id:
            return
        res = self._ctx.controllers.resources.get_resource(target_id)
        if res:
            self._current = self._ctx.serializer.serialize(res)
            self.currentReaderResourceChanged.emit()

    # ------------------------------------------------------------------ #
    # Okuyucuyu ac/kapat
    # ------------------------------------------------------------------ #

    @Slot(int)
    def openReader(self, resource_id: int) -> None:
        resource = self._ctx.controllers.resources.get_resource(resource_id)
        if not resource:
            return

        pdf_files = self._ctx.pdf_files
        self._current = self._ctx.serializer.serialize(resource)
        self.currentReaderResourceChanged.emit()
        if pdf_files.pdf_file_url(resource):
            self._navigate("pdfReader")
        elif looks_like_remote_pdf(resource.url) and not pdf_files.has_failed(resource.id):
            # Web PDF'i: once yerel diske indirilir, sonra native okuyucuda acilir.
            self._navigate("pdfReader")
            pdf_files.start_download(resource)
        else:
            self._navigate("reader")
        self._library.closeDrawer()

        # Eger tam metin bossa ve url varsa arka planda cikar. Indirilecek web
        # PDF'inde cikarim indirme bitince yerel dosyadan yapilir (cift indirme yok).
        if not resource.full_text and resource.url and not pdf_files.is_downloading(resource.id):
            self._ctx.extractor.schedule(resource.id, pdf_files.pdf_file_url(resource) or resource.url)

    @Slot()
    def closeReader(self) -> None:
        self._current = {}
        self.currentReaderResourceChanged.emit()
        self._navigate("showcase")

    @Slot(int)
    def openTextReader(self, resource_id: int) -> None:
        """Native PDF okuyucudan duz metin okuyucusuna gecis (indirme basarisiz
        olunca ya da kullanici isteyince)."""
        self._ctx.pdf_files.mark_failed(resource_id)
        self.refresh_current(resource_id)
        self._navigate("reader")

    def _on_pdf_download_finished(self, resource_id: int, path: str | None) -> None:
        resources = self._ctx.controllers.resources
        is_open = self._current.get("id") == resource_id
        if path:
            resource = resources.get_resource(resource_id)
            if resource is None:
                Path(path).unlink(missing_ok=True)
                return
            metadata = dict(resource.extra_metadata or {})
            metadata["local_pdf"] = path
            if resources.update_resource(resource_id, {"extra_metadata": metadata}) is None:
                Path(path).unlink(missing_ok=True)
                return
            self._library.reload()
            self._library.update_selected_if_matches(resource_id)
            if is_open:
                self.refresh_current(resource_id)
            if not resource.full_text:
                self._ctx.extractor.schedule(resource_id, Path(path).as_uri())
            return
        self._ctx.pdf_files.mark_failed(resource_id)
        resource = resources.get_resource(resource_id)
        if resource and resource.url and not resource.full_text:
            # Metin okuyucusu icin tam metin yine de cikarilmali.
            self._ctx.extractor.schedule(resource_id, resource.url)
        if is_open:
            self._ctx.notify.error(AppStrings.NOTIFICATION_PDF_DOWNLOAD_FAILED)
            self.refresh_current(resource_id)
            self._navigate("reader")

    def _on_full_text_extracted(self, resource_id: int, full_text: str) -> None:
        if self._current.get("id") == resource_id:
            self.refresh_current(resource_id)
            self.readerArticleUpdated.emit(resource_id, full_text)

    def _on_document_released(self, file_url: str) -> None:
        if self._pdf_outlines.pop(file_url, None) is not None:
            self.pdfOutlinesChanged.emit()

    # ------------------------------------------------------------------ #
    # Alinti
    # ------------------------------------------------------------------ #

    @Slot(int, str, str)
    @Slot(int, str, str, "QVariantMap")
    def addHighlight(
        self,
        resource_id: int,
        content: str,
        color: str = DEFAULT_HIGHLIGHT_COLOR,
        position: dict | None = None,
    ) -> None:
        """HTML okuyucudan alinti ekler. `position` (opsiyonel): {page, startIndex, length}."""
        if not content.strip():
            return
        self._save_highlight(resource_id, content.strip(), color, self._position_from_map(position))

    @staticmethod
    def _position_from_map(position: dict | None) -> HighlightPosition | None:
        if not position:
            return None
        page, start, length = (position.get(k, -1) for k in ("page", "startIndex", "length"))
        if page < 0 or start < 0 or length < 0:
            return None
        return HighlightPosition(int(page), int(start), int(length))

    def _save_highlight(
        self, resource_id: int, content: str, color: str, position: HighlightPosition | None
    ) -> None:
        result = self._ctx.controllers.highlights.create_highlight(resource_id, content, color, position)
        if result is None:
            return  # Hata zaten event_bus.error_occurred uzerinden toast olarak gosterildi
        self.reload_highlights()
        self.refresh_current(resource_id)
        self._ctx.notify.info(AppStrings.NOTIFICATION_HIGHLIGHT_SAVED)

    @Slot(int, str, "QVariantMap", str)
    def addPdfHighlight(self, resource_id: int, file_url: str, selection: dict, color: str) -> None:
        """PDF'te secili metni alinti olarak kaydeder. `selection`: {page, fromX, fromY, toX, toY}."""
        resolved = self._ctx.pdf_files.select_text(file_url, selection)
        if resolved is None:
            return
        _doc, page, pdf_selection = resolved
        start = pdf_selection.startIndex()
        position = HighlightPosition(page, start, pdf_selection.endIndex() - start)
        self._save_highlight(resource_id, sanitize_utf8(pdf_selection.text()), color, position)

    @Slot(int, str)
    def updateHighlightColor(self, highlight_id: int, color: str) -> None:
        if self._ctx.controllers.highlights.update_highlight_color(highlight_id, color) is None:
            return
        self.reload_highlights()
        self.refresh_current()

    @Slot(int, str)
    def updateHighlightComment(self, highlight_id: int, comment: str) -> None:
        if self._ctx.controllers.highlights.update_highlight_comment(highlight_id, comment) is None:
            return
        self.reload_highlights()
        self.refresh_current()

    @Slot(int)
    def deleteHighlight(self, highlight_id: int) -> None:
        if not self._ctx.controllers.highlights.delete_highlight(highlight_id):
            return
        self.reload_highlights()
        self.refresh_current()
        self._ctx.notify.info(AppStrings.NOTIFICATION_HIGHLIGHT_DELETED)

    @Slot("QVariantList")
    def deleteHighlights(self, highlight_ids: list) -> None:
        """Secili alintilari toplu siler (tek yenileme, tek bildirim)."""
        deleted = self._ctx.controllers.highlights.delete_highlights([int(i) for i in highlight_ids])
        if not deleted:
            return
        self.reload_highlights()
        self.refresh_current()
        self._ctx.notify.info(AppStrings.NOTIFICATION_HIGHLIGHTS_DELETED_FMT.format(count=deleted))

    # ------------------------------------------------------------------ #
    # Kelime
    # ------------------------------------------------------------------ #

    @Slot(int, str, str, str)
    def addVocabulary(self, resource_id: int, word: str, translation: str, context_sentence: str = "") -> None:
        if not word.strip() or not translation.strip():
            return
        result = self._ctx.controllers.vocabulary.create_vocabulary(
            resource_id, word.strip(), translation.strip(), context_sentence.strip() or None
        )
        if result is None:
            return
        self.reload_vocabulary()
        self._ctx.notify.info(AppStrings.NOTIFICATION_VOCAB_SAVED_FMT.format(word=word))

    @Slot(int)
    def deleteVocabulary(self, vocabulary_id: int) -> None:
        if not self._ctx.controllers.vocabulary.delete_vocabulary(vocabulary_id):
            return
        self.reload_vocabulary()
        self._ctx.notify.info(AppStrings.NOTIFICATION_VOCAB_DELETED)

    @Slot(int, str, "QVariantMap", str)
    def addPdfVocabulary(self, resource_id: int, file_url: str, selection: dict, translation: str) -> None:
        """PDF'te secili kelimeyi, gectigi cumleyle (baglam) birlikte kelime havuzuna ekler.
        `selection`: {page, fromX, fromY, toX, toY} (bkz. `PdfFileManager.select_text`)."""
        resolved = self._ctx.pdf_files.select_text(file_url, selection)
        if resolved is None:
            return
        doc, page, pdf_selection = resolved
        word = sanitize_utf8(pdf_selection.text()).strip()
        page_text = sanitize_utf8(doc.getSelectionAtIndex(page, 0, 1_000_000).text())
        start = pdf_selection.startIndex()
        context = extract_sentence(page_text, start, pdf_selection.endIndex() - start)
        self.addVocabulary(resource_id, " ".join(word.split()), translation, context)

    # ------------------------------------------------------------------ #
    # PDF notu
    # ------------------------------------------------------------------ #

    @Slot(int, int, float, float, str)
    def addPdfNote(self, resource_id: int, page: int, x: float, y: float, text: str) -> None:
        if not text.strip():
            return
        if self._ctx.controllers.pdf_notes.create_note(resource_id, page, x, y, text.strip()) is None:
            return
        self.refresh_current(resource_id)

    @Slot(int, str)
    def updatePdfNote(self, note_id: int, text: str) -> None:
        if not text.strip():
            return
        if self._ctx.controllers.pdf_notes.update_note(note_id, text.strip()) is None:
            return
        self.refresh_current()

    @Slot(int)
    def deletePdfNote(self, note_id: int) -> None:
        if self._ctx.controllers.pdf_notes.delete_note(note_id):
            self.refresh_current()

    # ------------------------------------------------------------------ #
    # PDF anahati
    # ------------------------------------------------------------------ #

    @Slot(str)
    def loadPdfOutline(self, file_url: str) -> None:
        """PDF anahatini arka planda okur (bkz. utils/pdf_outline.py); sonuc `pdfOutlines`'a yazilir.
        Dosya basina bir kez okunur (QML binding'i her alinti/not degisiminde yeniden calisir)."""
        if not file_url or file_url in self._pdf_outlines or file_url in self._pdf_outlines_loading:
            return
        self._pdf_outlines_loading.add(file_url)
        path = Path(QUrl(file_url).toLocalFile() or file_url)
        worker = PdfOutlineWorker(file_url, path)
        worker.signals.finished.connect(self._on_pdf_outline_loaded)
        self._ctx.thread_pool.start(worker)

    def _on_pdf_outline_loaded(self, file_url: str, outline: list) -> None:
        self._pdf_outlines_loading.discard(file_url)
        self._pdf_outlines[file_url] = outline
        self.pdfOutlinesChanged.emit()

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
        if self._current.get("id") == resource_id:
            self.refresh_current(resource_id)
        self._ctx.notify.info(AppStrings.NOTIFICATION_PAPER_METADATA_SAVED)

    # ------------------------------------------------------------------ #
    # Referans / atif yapanlar (OpenAlex)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _empty_related_papers() -> dict:
        blank = {"loading": False, "error": "", "loaded": False, "items": []}
        return {"openalexId": "", "references": dict(blank), "citations": dict(blank)}

    @Slot(int)
    def loadRelatedPapers(self, resource_id: int) -> None:
        """Okuyucudaki makalenin referanslarini ve ona atif yapanlari (OpenAlex) yukler."""
        resource = self._ctx.controllers.resources.get_resource(resource_id)
        openalex_id = ((resource.extra_metadata or {}).get("openalex_id") if resource else "") or ""
        self._related_papers = self._empty_related_papers()
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

    # ------------------------------------------------------------------ #
    # Markdown disa aktarim
    # ------------------------------------------------------------------ #

    @Slot(int, str)
    def exportResourceMarkdown(self, resource_id: int, file_url: str) -> None:
        resource = self._ctx.controllers.resources.get_resource(resource_id)
        if resource is None:
            return
        write_export(file_url, ExportService.resource_markdown(resource), self._ctx.notify)

    @Slot(str)
    def exportLibraryMarkdown(self, file_url: str) -> None:
        resources = self._ctx.controllers.resources.load_resources_with_filters({})
        if not any(ExportService.has_content(r) for r in resources):
            self._ctx.notify.info(AppStrings.NOTIFICATION_EXPORT_EMPTY)
            return
        write_export(file_url, ExportService.library_markdown(resources), self._ctx.notify)
