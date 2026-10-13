from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from core.logger import log
from pdfkit.api import MatrixFilter, MatrixRow, column_keys, column_name, document_ids_matching, make_matrix, render_markdown, tag_counts
from ui_qml.bridges.reader_bridge import ReaderBridge
from ui_qml.context import BridgeContext
from ui_qml.file_export import write_export
from ui_qml.serializers import serialize_matrix

REFRESH_MS = 300  # alinti yazma sikligi: matris acikken tek tazelemeye birlesir


class SynthesisBridge(QObject):
    """Bilgi Havuzu > Matris: literatur matrisi (satir = makale, sutun = anlam etiketi, hucre = alintilar). Matris ve
    suzgec mantigi `pdfkit`'tedir; burasi suzgec durumunu tutar, veriyi QML'e verir, hucredeki alintiya tiklaninca
    okuyucuyu o alintida acar ve suzulmus matrisi Markdown olarak disa aktarir/panoya kopyalar.

    Veritabani okumasi yalniz matris GORUNURKEN (`setActive`) ve veri degistiyse yapilir; suzgec degisimi onbellekteki
    satirlardan hesaplanir (veritabanina gitmez)."""

    matrixChanged = Signal()
    filterChanged = Signal()

    def __init__(self, ctx: BridgeContext, reader: ReaderBridge, pdf_bridge: QObject, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._reader = reader
        self._pdf = pdf_bridge
        self._rows: list[MatrixRow] = []
        self._matrix: dict = serialize_matrix(make_matrix([]))
        self._tags: list[dict] = []
        self._labels: set[str] = set()  # bos = tum sutunlar
        self._tag = ""
        self._title = ""
        self._active = False
        self._dirty = True
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self.reload)
        pdf_bridge.contentChanged.connect(self._on_content_changed)

    # ------------------------------------------------------------------ #
    # Durum
    # ------------------------------------------------------------------ #

    @Property(dict, notify=matrixChanged)
    def matrix(self) -> dict:
        return self._matrix

    @Property(list, notify=matrixChanged)
    def tags(self) -> list:
        """Alintilardaki serbest etiketler: [{name, count}]."""
        return self._tags

    @Property(list, notify=filterChanged)
    def activeLabels(self) -> list:
        return sorted(self._labels, key=column_keys().index)

    @Property(str, notify=filterChanged)
    def tag(self) -> str:
        return self._tag

    @Property(str, notify=filterChanged)
    def titleQuery(self) -> str:
        return self._title

    @Property(bool, notify=filterChanged)
    def filtered(self) -> bool:
        return bool(self._labels or self._tag or self._title.strip())

    # ------------------------------------------------------------------ #
    # Suzgecler
    # ------------------------------------------------------------------ #

    @Slot(str)
    def toggleLabel(self, key: str) -> None:
        if key not in column_keys():
            return
        self._labels ^= {key}
        self._after_filter_change()

    @Slot(str)
    def setTag(self, tag: str) -> None:
        """Serbest etikete gore suzer; ayni etiket yeniden verilirse ya da bos dizgeyle suzgec kalkar."""
        tag = (tag or "").strip().lstrip("#").lower()
        self._tag = "" if tag == self._tag else tag
        self._after_filter_change()

    @Slot(str)
    def setTitleQuery(self, text: str) -> None:
        self._title = text or ""
        self._after_filter_change()

    @Slot()
    def clearFilters(self) -> None:
        self._labels.clear()
        self._tag, self._title = "", ""
        self._after_filter_change()

    def _after_filter_change(self) -> None:
        self.filterChanged.emit()
        self._recompute()

    # ------------------------------------------------------------------ #
    # Veri
    # ------------------------------------------------------------------ #

    @Slot(bool)
    def setActive(self, active: bool) -> None:
        """Matris sekmesi gorunur mu? Gorunur olunca (ve veri degistiyse) veritabanindan yenilenir."""
        self._active = active
        if active and self._dirty:
            self.reload()

    @Slot()
    def reload(self) -> None:
        try:
            self._rows = self._ctx.pdf_library.synthesis().rows()
        except Exception:
            log.exception("Literatur matrisi yuklenemedi")
            self._rows = []
        self._dirty = False
        self._tags = [{"name": name, "count": count} for name, count in tag_counts(self._rows)]
        self._recompute()

    def _on_content_changed(self, _resource_id: int) -> None:
        self._dirty = True
        if self._active:
            self._timer.start()

    def _current_matrix(self):
        flt = MatrixFilter(
            labels=tuple(sorted(self._labels, key=column_keys().index)) or None,
            tag=self._tag or None,
            document_ids=document_ids_matching(self._rows, self._title),
        )
        return make_matrix(self._rows, flt)

    def _recompute(self) -> None:
        self._matrix = serialize_matrix(self._current_matrix())
        self.matrixChanged.emit()

    # ------------------------------------------------------------------ #
    # Eylemler
    # ------------------------------------------------------------------ #

    @Slot(int, int, str)
    def openAnnotation(self, resource_id: int, page: int, annotation_uid: str) -> None:
        """Hucredeki alintiya tiklandi: okuyucu o alintida (ya da sayfada) acilir."""
        self._pdf.requestJump(resource_id, page, annotation_uid)
        self._reader.openReader(resource_id)

    def _filter_note(self) -> str:
        parts = [column_name(key) for key in sorted(self._labels, key=column_keys().index)]
        if self._tag:
            parts.append(f"#{self._tag}")
        if self._title.strip():
            parts.append(f"kaynak: {self._title.strip()}")
        return " · ".join(parts)

    def markdown(self) -> str:
        """Ekrandaki (suzulmus) matrisin Markdown'i."""
        return render_markdown(self._current_matrix(), note=self._filter_note())

    @Slot(str)
    def exportMarkdown(self, file_url: str) -> None:
        if not self._matrix["rowCount"]:
            self._ctx.notify.info("Dışa aktarılacak alıntı yok.")
            return
        write_export(file_url, self.markdown(), self._ctx.notify)

    @Slot()
    def copyMarkdown(self) -> None:
        if not self._matrix["rowCount"]:
            self._ctx.notify.info("Kopyalanacak alıntı yok.")
            return
        QGuiApplication.clipboard().setText(self.markdown())
        self._ctx.notify.info("Matris Markdown olarak panoya kopyalandı.")
