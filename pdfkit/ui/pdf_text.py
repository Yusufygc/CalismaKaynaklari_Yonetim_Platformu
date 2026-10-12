from PySide6.QtCore import qVersion
from PySide6.QtPdf import QPdfDocument, QPdfSelection

from pdfkit.domain.annotations import Segment
from pdfkit.domain.text import sanitize_text

_WHOLE_PAGE = 1_000_000


def current_engine_fp() -> str:
    """Alinti indekslerini ureten motorun parmak izi (Qt surumu); farkliysa geometri/konum yeniden dogrulanir."""
    return f"qtpdf-{qVersion()}"


class QtPageTextProvider:
    """`PageTextProvider`'in Qt uygulamasi: alinti indeksleriyle ayni indeks uzayi (QPdfDocument). Yalnizca
    belgenin yasadigi thread'de (UI) kullanilir. Sayfa metinleri onbelleklenir."""

    def __init__(self, document: QPdfDocument) -> None:
        self._document = document
        self._cache: dict[int, str] = {}

    def page_count(self) -> int:
        return self._document.pageCount()

    def text_of(self, page: int) -> str:
        if page not in self._cache:
            self._cache[page] = sanitize_text(self._document.getSelectionAtIndex(page, 0, _WHOLE_PAGE).text())
        return self._cache[page]


def segment_from_selection(page: int, selection: QPdfSelection) -> Segment:
    """Gecerli bir QPdfSelection'dan parca uretir: metin indeksleri + sayfa noktasi poligonlari.

    Poligonlar secim aninda hazirdir; ayrica `getSelectionAtIndex` hesabi gerekmez (spike S2: ikisi birebir
    ayni, bkz. docs/plans/pdfkit-faz0-raporu.md)."""
    polygons = [[(point.x(), point.y()) for point in polygon] for polygon in selection.bounds()]
    return Segment(
        page=page,
        start=selection.startIndex(),
        end=selection.endIndex(),
        text=sanitize_text(selection.text()),
        polygons=polygons or None,
    )
