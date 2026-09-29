from tests.pdf_factory import write_outline_pdf
from utils.pdf_outline import read_outline


def test_read_outline_returns_titles_levels_and_pages(tmp_path):
    pdf = write_outline_pdf(tmp_path / "anahat.pdf", ["Giris", "Yontem", "Sonuc"])

    items = read_outline(pdf)

    assert items == [
        {"title": "Giris", "level": 0, "page": 0},
        {"title": "Yontem", "level": 0, "page": 1},
        {"title": "Sonuc", "level": 0, "page": 2},
    ]


def test_read_outline_reports_nested_levels(tmp_path):
    from pypdf import PdfWriter

    pdf = tmp_path / "ic_ice.pdf"
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=200, height=200)
    parent = writer.add_outline_item("Bolum 1", 0)
    writer.add_outline_item("Alt baslik", 1, parent=parent)
    writer.add_outline_item("Bolum 2", 2)
    with open(pdf, "wb") as handle:
        writer.write(handle)

    items = read_outline(pdf)

    assert [(i["title"], i["level"], i["page"]) for i in items] == [
        ("Bolum 1", 0, 0), ("Alt baslik", 1, 1), ("Bolum 2", 0, 2),
    ]


def test_read_outline_without_bookmarks_is_empty(tmp_path):
    from pypdf import PdfWriter

    pdf = tmp_path / "duz.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with open(pdf, "wb") as handle:
        writer.write(handle)

    assert read_outline(pdf) == []


def test_read_outline_returns_empty_for_unreadable_file(tmp_path):
    broken = tmp_path / "bozuk.pdf"
    broken.write_bytes(b"bu bir pdf degil")

    assert read_outline(broken) == []
    assert read_outline(tmp_path / "yok.pdf") == []
