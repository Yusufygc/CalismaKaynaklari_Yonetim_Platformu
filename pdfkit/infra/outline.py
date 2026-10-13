from pathlib import Path

import pypdfium2 as pdfium

from core.logger import log
from pdfkit.infra.inspector import PDFIUM_LOCK


def read_outline(pdf_path: Path) -> list[dict]:
    """PDF anahatini (icindekiler) duz listeye cevirir: [{title, level, page}] (`page` 0 tabanli).

    Qt'nin `QPdfBookmarkModel`'i bozuk yer imli PDF'lerde baslatilmamis bellek okuyup uygulamayi cokertiyordu (canli
    kullanimda dogrulandi); bu yuzden Qt'nin bookmark kodu hic kullanilmaz, anahat `pypdfium2` ile okunur. Sayfa disinda
    konum tasinmaz (bolume gitmek icin sayfa yeterli). Cozumlenemeyen yer imi atlanir; dosya acilamazsa/okunamazsa bos
    liste doner (log'lanir)."""
    try:
        with PDFIUM_LOCK:
            pdf = pdfium.PdfDocument(str(pdf_path))
            try:
                page_count = len(pdf)
                return list(_items(pdf, page_count, pdf_path))
            finally:
                pdf.close()
    except Exception:
        log.exception("PDF anahati okunamadi: %s", pdf_path)
        return []


def _items(pdf: "pdfium.PdfDocument", page_count: int, pdf_path: Path):
    for bookmark in pdf.get_toc():
        try:
            title = (bookmark.get_title() or "").strip()
            dest = bookmark.get_dest()
            page = dest.get_index() if dest is not None else None
        except Exception:
            log.debug("PDF yer imi cozumlenemedi (%s)", pdf_path)
            continue
        if title and isinstance(page, int) and 0 <= page < page_count:
            yield {"title": title, "level": bookmark.level, "page": page}
