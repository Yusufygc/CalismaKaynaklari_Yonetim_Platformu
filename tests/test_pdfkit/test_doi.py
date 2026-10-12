import pytest

from pdfkit.domain.doi import extract_doi


@pytest.mark.parametrize(
    "text,expected",
    [
        ("DOI: 10.1038/nature14539.", "10.1038/nature14539"),
        ("https://doi.org/10.1109/CVPR.2016.90, IEEE", "10.1109/cvpr.2016.90"),
        ("bkz. (10.48550/arXiv.1706.03762)", "10.48550/arxiv.1706.03762"),
        ("iki doi: 10.1000/a ve 10.2000/b", "10.1000/a"),
        ("doi yok, sadece 10.5 sayisi", None),
        ("", None),
        (None, None),
    ],
)
def test_extract_doi(text, expected):
    assert extract_doi(text) == expected
