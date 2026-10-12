import re
import threading
from pathlib import Path

import pypdfium2 as pdfium

from pdfkit.domain.doi import extract_doi
from pdfkit.domain.errors import NotAPdfError
from pdfkit.domain.models import PdfInspection

_SAMPLE_PAGES = 5  # metin katmani tespiti icin bakilan ilk sayfa sayisi
_DOI_PAGES = 2  # DOI aranan ilk sayfa sayisi
_MIN_ALNUM_PER_PAGE = 40
_JUNK_TITLE = re.compile(r"^(microsoft word\b|untitled|adsiz|document\d*$)|\.(docx?|tex|indd)$", re.IGNORECASE)

# PDFium thread-safe degildir; ayni surecteki tum pypdfium2 cagrilari tek kilitle siralanir.
PDFIUM_LOCK = threading.RLock()


def _clean(value: str | None) -> str | None:
    text = " ".join((value or "").split())
    return text or None


def _usable_title(raw: str | None) -> str | None:
    title = _clean(raw)
    if title is None or len(title) < 4 or _JUNK_TITLE.search(title):
        return None
    return title


def inspect_pdf(path: Path) -> PdfInspection:
    """PDF'i acip sayfa sayisi, metin katmani varligi, metadata ve DOI'yi cikarir.

    pypdfium2 kullanilir (C, GIL'i birakir); metin indeksleri alinti capasi icin KULLANILMAZ (Qt'nin kendi
    PDFium'unun indeksleri ile birebir ayni olmayabilir)."""
    with PDFIUM_LOCK:
        try:
            pdf = pdfium.PdfDocument(str(path))
        except (pdfium.PdfiumError, OSError) as exc:
            raise NotAPdfError(f"PDF acilamadi: {path.name} ({exc})") from exc
        try:
            page_count = len(pdf)
            if page_count == 0:
                raise NotAPdfError(f"PDF bos: {path.name}")
            metadata = pdf.get_metadata_dict()
            sampled = [page_text(pdf, index) for index in range(min(page_count, _SAMPLE_PAGES))]
        finally:
            pdf.close()

    has_text = any(sum(ch.isalnum() for ch in text) >= _MIN_ALNUM_PER_PAGE for text in sampled)
    front_text = " ".join(sampled[:_DOI_PAGES])
    doi = extract_doi(metadata.get("Subject")) or extract_doi(metadata.get("Keywords")) or extract_doi(front_text)
    return PdfInspection(
        page_count=page_count,
        has_text_layer=has_text,
        title=_usable_title(metadata.get("Title")),
        author=_clean(metadata.get("Author")),
        doi=doi,
    )


def page_text(pdf: "pdfium.PdfDocument", index: int) -> str:
    """Acik belgenin `index`. sayfasinin duz metni (cagiran PDFIUM_LOCK'u tutmali)."""
    page = pdf[index]
    try:
        textpage = page.get_textpage()
        try:
            return textpage.get_text_bounded()
        finally:
            textpage.close()
    finally:
        page.close()
