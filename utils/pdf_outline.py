from pathlib import Path

from pypdf import PdfReader

from core.logger import log


def read_outline(pdf_path: Path) -> list[dict]:
    """PDF anahatini (icindekiler) `pypdf` ile duz listeye cevirir: [{title, level, page}].

    Qt'nin `QPdfBookmarkModel`'i bozuk yer imli PDF'lerde baslatilmamis bellek
    okuyup (`qt.pdf.bookmarks: bookmark with invalid location and/or zoom ...`)
    uygulamayi cokertiyordu (canli kullanimda dogrulandi); bu yuzden Qt'nin
    bookmark kodu hic kullanilmaz. Sayfa disinda konum tasinmaz -- bolume gitmek
    icin sayfa yeterli. Hata durumunda bos liste doner (log'lanir).
    """
    try:
        reader = PdfReader(str(pdf_path))
        page_count = len(reader.pages)
        items: list[dict] = []

        def walk(nodes: list, level: int) -> None:
            for node in nodes:
                if isinstance(node, list):
                    walk(node, level + 1)
                    continue
                title = str(getattr(node, "title", "") or "").strip()
                try:
                    page = reader.get_destination_page_number(node)
                except Exception:
                    continue
                if title and isinstance(page, int) and 0 <= page < page_count:
                    items.append({"title": title, "level": level, "page": page})

        walk(reader.outline, 0)
        return items
    except Exception:
        log.exception("PDF anahati okunamadi: %s", pdf_path)
        return []
