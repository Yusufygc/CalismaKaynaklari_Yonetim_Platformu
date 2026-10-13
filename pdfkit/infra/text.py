from collections.abc import Iterator
from pathlib import Path

import pypdfium2 as pdfium

from pdfkit.domain.errors import NotAPdfError
from pdfkit.infra.inspector import PDFIUM_LOCK, page_text


def extract_page_texts(data: bytes) -> list[str]:
    """PDF'in her sayfasinin duz metnini dondurur (pypdfium2: C, GIL'i birakir; pypdf'ten ~15 kat hizli).

    Kitaplik geneli arama ve metin okuyucusu icindir; alinti capasi indeksleri icin KULLANILMAZ (Qt'nin kendi
    PDFium'unun indeksleriyle birebir ayni olmayabilir). Acilamayan PDF'te `NotAPdfError`."""
    with PDFIUM_LOCK:
        try:
            pdf = pdfium.PdfDocument(data)
        except pdfium.PdfiumError as exc:
            raise NotAPdfError(f"PDF acilamadi: {exc}") from exc
        try:
            return [page_text(pdf, index) for index in range(len(pdf))]
        finally:
            pdf.close()



def iter_page_texts(path: Path, max_pages: int | None = None) -> Iterator[str]:
    """PDF'in sayfa metinlerini TEK TEK uretir (tam metin dizini icin). PDFium kilidi yalniz sayfa basina tutulur:
    uzun bir belge indekslenirken ice aktarma/inceleme gibi diger PDFium isleri araya girebilir, cagiran sayfalar
    arasinda iptal edebilir. Acilamayan PDF'te `NotAPdfError`. Yarida birakilirsa `close()` belgeyi kapatir."""
    with PDFIUM_LOCK:
        try:
            pdf = pdfium.PdfDocument(str(path))
        except (pdfium.PdfiumError, OSError) as exc:
            raise NotAPdfError(f"PDF acilamadi: {path.name} ({exc})") from exc
        total = len(pdf) if max_pages is None else min(len(pdf), max_pages)
    try:
        for index in range(total):
            with PDFIUM_LOCK:
                text = page_text(pdf, index)
            yield text
    finally:
        with PDFIUM_LOCK:
            pdf.close()
