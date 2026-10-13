"""PDFium ile sayfadaki aranan metnin konumu (okuyucu o satira atlasin diye)."""
import pytest

from pdfkit.infra.text import locate_text
from tests.pdf_factory import write_multipage_text_pdf

LINES = [f"satir numarasi {i} burada uzun bir cumle olsun" for i in range(30)] + ["zebramarker son satir"]


@pytest.fixture()
def pdf(tmp_path):
    return write_multipage_text_pdf(tmp_path / "konum.pdf", [LINES, ["ikinci sayfa ozel kelime papatya burada"]])


def test_the_position_is_top_left_origin_page_points_like_the_annotation_rects(pdf):
    first = locate_text(pdf, 0, "satir numarasi 0")
    twenty = locate_text(pdf, 0, "satir numarasi 20")

    assert first is not None and twenty is not None
    assert first[0] == pytest.approx(72, abs=2)  # sol kenar boslugu
    assert first[1] == pytest.approx(792 - 700 - 12, abs=14)  # ilk satir sayfanin ustune yakin (y asagi dogru artar)
    assert twenty[1] - first[1] == pytest.approx(20 * 20, abs=2)  # satir araligi 20 nokta, asagi dogru


def test_search_ignores_case_and_returns_none_when_there_is_nothing_to_find(pdf, tmp_path):
    assert locate_text(pdf, 1, "PAPATYA") is not None
    assert locate_text(pdf, 0, "papatya") is None  # baska sayfada
    assert locate_text(pdf, 5, "satir") is None  # sayfa yok
    assert locate_text(pdf, -1, "satir") is None
    assert locate_text(pdf, 0, "   ") is None
    broken = tmp_path / "bozuk.pdf"
    broken.write_bytes(b"pdf degil")
    assert locate_text(broken, 0, "satir") is None
    assert locate_text(tmp_path / "yok.pdf", 0, "satir") is None
