import pytest
from pypdf import PdfWriter

from pdfkit.domain.errors import NotAPdfError
from pdfkit.infra.inspector import inspect_pdf
from tests.pdf_factory import write_text_pdf

LINES = [
    "Derin ogrenme ile dogal dil isleme uzerine bir inceleme calismasi sunulmaktadir.",
    "Kaynak: https://doi.org/10.1038/nature14539. Ikinci satir ek aciklama icerir.",
]


def _blank_pdf(path, metadata=None):
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    if metadata:
        writer.add_metadata(metadata)
    with open(path, "wb") as handle:
        writer.write(handle)
    return path


def test_text_pdf_reports_pages_text_layer_and_doi(tmp_path):
    result = inspect_pdf(write_text_pdf(tmp_path / "makale.pdf", LINES))

    assert result.page_count == 1
    assert result.has_text_layer is True
    assert result.doi == "10.1038/nature14539"


def test_scanned_like_pdf_without_text_layer_is_flagged(tmp_path):
    result = inspect_pdf(_blank_pdf(tmp_path / "tarama.pdf"))

    assert result.page_count == 1
    assert result.has_text_layer is False
    assert result.doi is None


def test_metadata_title_and_author_are_cleaned(tmp_path):
    path = _blank_pdf(tmp_path / "a.pdf", {"/Title": "Attention Is  All You Need", "/Author": "  Ada   Lovelace "})

    result = inspect_pdf(path)

    assert result.title == "Attention Is All You Need"
    assert result.author == "Ada Lovelace"


def test_placeholder_titles_are_dropped(tmp_path):
    path = _blank_pdf(tmp_path / "b.pdf", {"/Title": "Microsoft Word - taslak.docx"})

    assert inspect_pdf(path).title is None


def test_garbage_file_raises_not_a_pdf(tmp_path):
    path = tmp_path / "bozuk.pdf"
    path.write_bytes(b"bu bir pdf degil")

    with pytest.raises(NotAPdfError):
        inspect_pdf(path)
