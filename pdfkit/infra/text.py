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

