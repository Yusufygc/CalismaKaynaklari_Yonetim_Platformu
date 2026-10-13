from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from core.logger import log
from ui_qml.bridges.reader_bridge import ReaderBridge
from ui_qml.context import BridgeContext
from ui_qml.serializers import serialize_search_group

DEBOUNCE_MS = 250  # yazarken her tusta degil, duraklayinca aranir (arama ana thread'de ~50 ms surebilir)


class SearchBridge(QObject):
    """Kutuphane geneli tam metin aramasi (Bilgi Havuzu > Metinde Ara): PDF'lerin icindeki metin. Dizin ve arama
    `pdfkit`'tedir; burasi sorguyu bekletip sonucu QML'e verir ve sonuca tiklaninca okuyucuyu o sayfada acar."""

    resultsChanged = Signal()
    statusChanged = Signal()

    def __init__(self, ctx: BridgeContext, reader: ReaderBridge, pdf_bridge: QObject, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._reader = reader
        self._pdf = pdf_bridge
        self._query = ""
        self._groups: list[dict] = []
        self._searched = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(DEBOUNCE_MS)
        self._timer.timeout.connect(self._run)
        indexer = ctx.text_indexer
        indexer.statusChanged.connect(self.statusChanged)
        indexer.finished.connect(self._on_index_finished)  # dizin buyuyunce acik arama tazelenir

    @Property(str, notify=resultsChanged)
    def query(self) -> str:
        return self._query

    @Property(list, notify=resultsChanged)
    def groups(self) -> list:
        """[{resourceId, title, hits: [{page (0 tabanli), html}], more}], en alakali kaynak once."""
        return self._groups

    @Property(bool, notify=resultsChanged)
    def searched(self) -> bool:
        """Bos olmayan bir sorgu arandi mi? (Sonuc yoksa "bulunamadi" ile "henuz aranmadi" ayrimi icin.)"""
        return self._searched

    @Property(dict, notify=statusChanged)
    def indexStatus(self) -> dict:
        """{state: idle|running|unavailable, done, total, pending}."""
        return self._ctx.text_indexer.status()

    @Slot(str)
    def search(self, text: str) -> None:
        """Sorguyu ayarlar; kisa bir duraklamadan sonra arar. Bos sorgu hemen sonuclari temizler."""
        self._query = text
        if not text.strip():
            self._timer.stop()
            self._groups, self._searched = [], False
            self.resultsChanged.emit()
            return
        self._timer.start()

    @Slot()
    def clear(self) -> None:
        self.search("")

    @Slot(int, int)
    def openHit(self, resource_id: int, page: int) -> None:
        """Sonuca tiklandi: okuyucu `page` (0 tabanli) sayfasinda acilir."""
        self._pdf.requestJump(resource_id, page, "")
        self._reader.openReader(resource_id)

    def _run(self) -> None:
        text = self._query
        try:
            groups = self._ctx.pdf_library.searching().search_by_resource(text)
        except Exception:
            log.exception("Tam metin aramasi basarisiz")
            groups = []
        self._groups = [serialize_search_group(group) for group in groups]
        self._searched = True
        self.resultsChanged.emit()

    def _on_index_finished(self) -> None:
        if self._searched and self._query.strip():
            self._run()
