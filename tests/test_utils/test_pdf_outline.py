import pytest

from utils.pdf_outline import read_outline


def test_read_outline_on_real_pdf():
    from core.paths import pdf_storage_dir

    candidates = list(pdf_storage_dir().glob("*Hafta*.pdf")) if pdf_storage_dir().exists() else []
    if not candidates:
        pytest.skip("Gercek anahatli test PDF'i yok")

    items = read_outline(candidates[0])

    assert len(items) > 5
    assert all({"title", "level", "page"} <= set(i) for i in items)
    assert all(i["page"] >= 0 for i in items)


def test_read_outline_returns_empty_for_unreadable_file(tmp_path):
    broken = tmp_path / "bozuk.pdf"
    broken.write_bytes(b"bu bir pdf degil")

    assert read_outline(broken) == []
    assert read_outline(tmp_path / "yok.pdf") == []
