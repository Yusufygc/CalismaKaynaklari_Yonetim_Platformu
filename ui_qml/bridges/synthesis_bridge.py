from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from core.events import event_bus
from core.logger import log
from pdfkit.api import (
    MatrixFilter,
    MatrixOptions,
    MatrixRow,
    color_for_label,
    column_keys,
    column_name,
    document_ids_matching,
    make_matrix,
    ordered_columns,
    render_markdown,
    tag_counts,
    with_provisional_citekeys,
)
from ui_qml.bridges.reader_bridge import ReaderBridge
from ui_qml.context import SETTING_MATRIX_CELL_LIMIT, SETTING_MATRIX_COLUMNS, SETTING_MATRIX_VAULT_COLUMNS, BridgeContext
from ui_qml.file_export import write_export
from ui_qml.serializers import serialize_matrix

REFRESH_MS = 300  # alinti yazma sikligi: matris acikken tek tazelemeye birlesir


class SynthesisBridge(QObject):
    """Bilgi Havuzu > Matris: literatur matrisi (satir = makale, sutun = anlam etiketi, hucre = alintilar). Matris ve
    suzgec mantigi `pdfkit`'tedir; burasi suzgec durumunu tutar, veriyi QML'e verir, hucredeki alintiya tiklaninca
    okuyucuyu o alintida acar ve suzulmus matrisi Markdown olarak disa aktarir/panoya kopyalar.

    Veritabani okumasi yalniz matris GORUNURKEN (`setActive`) ve veri degistiyse yapilir; suzgec degisimi onbellekteki
    satirlardan hesaplanir (veritabanina gitmez). Veri degisince yalniz degisen belgelerin satirlari yeniden okunur
    (ilk yukleme ya da bilinmeyen degisiklik tum kutuphaneyi okur)."""

    matrixChanged = Signal()
    filterChanged = Signal()
    optionsChanged = Signal()

    def __init__(self, ctx: BridgeContext, reader: ReaderBridge, pdf_bridge: QObject, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._reader = reader
        self._pdf = pdf_bridge
        self._rows: list[MatrixRow] = []  # onerilen atif anahtarlari eklenmis, suzgeclenecek satirlar
        self._by_document: dict[int, MatrixRow] = {}
        self._options = ctx.matrix_options()
        self._matrix: dict = serialize_matrix(make_matrix([]))
        self._tags: list[dict] = []
        self._labels: set[str] = set()  # bos = tum sutunlar
        self._tag = ""
        self._title = ""
        self._active = False
        self._dirty_all = True  # tum kutuphane okunmali (ilk yukleme / bilinmeyen degisiklik)
        self._dirty_documents: set[int] = set()  # yalniz bu belgelerin satirlari yenilenmeli
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._refresh)
        pdf_bridge.contentChanged.connect(self._on_content_changed)
        event_bus.resource_updated.connect(self._on_content_changed)  # baslik/yazar/yil duzenlemesi satiri etkiler
        event_bus.resource_deleted.connect(self._on_resource_deleted)

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
        return self._sorted_labels()

    def _order(self) -> tuple[str, ...]:
        return ordered_columns(self._options.order)

    def _sorted_labels(self) -> list[str]:
        return sorted(self._labels, key=self._order().index)

    # ------------------------------------------------------------------ #
    # Ayarlar (Ayarlar > Matris)
    # ------------------------------------------------------------------ #

    @Property(list, notify=optionsChanged)
    def columnSettings(self) -> list:
        """Ayarlar > Matris: [{key, name, color, vault}] kullanicinin sutun sirasiyla; `vault` o sutun Obsidian
        `_Matris.md`'ye yazilir mi."""
        chosen = self._options.vault_columns
        return [
            {"key": key, "name": column_name(key), "color": color_for_label(key) or "", "vault": chosen is None or key in chosen}
            for key in self._order()
        ]

    @Property(int, notify=optionsChanged)
    def cellLimit(self) -> int:
        return self._options.cell_limit

    @Slot(str, int)
    def moveColumn(self, key: str, delta: int) -> None:
        """Sutunu `delta` kadar kaydirir (-1 sola/yukari, +1 saga/asagi)."""
        order = list(self._order())
        if key not in order:
            return
        index = order.index(key)
        target = max(0, min(len(order) - 1, index + delta))
        if target == index:
            return
        order.insert(target, order.pop(index))
        self._apply_options(order=order)

    @Slot(str, bool)
    def setVaultColumn(self, key: str, enabled: bool) -> None:
        """`key` sutunu Obsidian matrisine yazilsin mi."""
        if key not in column_keys():
            return
        current = set(column_keys() if self._options.vault_columns is None else self._options.vault_columns)
        current.add(key) if enabled else current.discard(key)
        self._apply_options(vault_columns=[k for k in self._order() if k in current])

    @Slot(int)
    def setCellLimit(self, limit: int) -> None:
        """Obsidian matrisinde hucre basina en cok alinti (0 = hepsi)."""
        self._apply_options(cell_limit=limit)

    @Slot()
    def resetOptions(self) -> None:
        for key in (SETTING_MATRIX_COLUMNS, SETTING_MATRIX_VAULT_COLUMNS, SETTING_MATRIX_CELL_LIMIT):
            self._ctx.user_settings.set(key, None)
        self._options = self._ctx.matrix_options()
        self._options_applied()

    def _apply_options(self, order=None, vault_columns=..., cell_limit=None) -> None:
        current = self._options
        options = MatrixOptions.normalized(
            order if order is not None else list(current.order),
            current.vault_columns if vault_columns is ... else vault_columns,
            current.cell_limit if cell_limit is None else cell_limit,
        )
        settings = self._ctx.user_settings
        saved = (
            settings.set(SETTING_MATRIX_COLUMNS, list(options.order) or None)
            and settings.set(SETTING_MATRIX_VAULT_COLUMNS, None if options.vault_columns is None else list(options.vault_columns))
            and settings.set(SETTING_MATRIX_CELL_LIMIT, options.cell_limit)
        )
        if not saved:
            self._ctx.notify.error("Ayar kaydedilemedi.")
            return
        self._options = options
        self._options_applied()

    def _options_applied(self) -> None:
        self._ctx.vault_sync.set_matrix_options(self._options)
        self.optionsChanged.emit()
        self.filterChanged.emit()
        self._recompute()

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
        if active and (self._dirty_all or self._dirty_documents):
            self._refresh()

    @Slot()
    def reload(self) -> None:
        """Tum kutuphaneyi yeniden okur."""
        self._dirty_all = True
        self._refresh()

    def _refresh(self) -> None:
        library = self._ctx.pdf_library
        try:
            if self._dirty_all:
                self._by_document = {row.document.id: row for row in library.synthesis().rows()}
            elif self._dirty_documents:
                ids = sorted(self._dirty_documents)
                for document_id in ids:
                    self._by_document.pop(document_id, None)
                self._by_document.update({row.document.id: row for row in library.synthesis().rows_for(ids)})
        except Exception:
            log.exception("Literatur matrisi yuklenemedi")
            self._by_document = {}
        self._dirty_all, self._dirty_documents = False, set()
        self._rows = with_provisional_citekeys(self._by_document.values())
        self._tags = [{"name": name, "count": count} for name, count in tag_counts(self._rows)]
        self._recompute()

    def _on_content_changed(self, resource_id: int) -> None:
        document = self._ctx.pdf_library.documents().document_for_resource(resource_id)
        if document is None:
            return  # PDF'i olmayan kaynak (web makalesi) matrisi etkilemez
        self._dirty_documents.add(document.id)
        if self._active:
            self._timer.start()

    def _on_resource_deleted(self, _resource_id: int) -> None:
        self._dirty_all = True  # belgesi artik hangi kaynaga bagli bilinmez: tam okuma
        if self._active:
            self._timer.start()

    def _current_matrix(self):
        flt = MatrixFilter(
            labels=tuple(self._sorted_labels()) or None,
            tag=self._tag or None,
            document_ids=document_ids_matching(self._rows, self._title),
        )
        return make_matrix(self._rows, flt, order=self._options.order)

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
        parts = [column_name(key) for key in self._sorted_labels()]
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
