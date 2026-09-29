import pytest

from services.citation_service import CitationService

META = {
    "authors": ["Ashish Vaswani", "Noam M. Shazeer", "Niki Parmar"],
    "year": 2017,
    "venue": "Advances in Neural Information Processing Systems",
    "doi": "https://doi.org/10.5555/3295222.3295349",
}
TITLE = "Attention Is All You Need"


def test_apa_format():
    text = CitationService.format(TITLE, META, "apa")
    assert text == (
        "Vaswani, A., Shazeer, N. M., & Parmar, N. (2017). Attention Is All You Need. "
        "Advances in Neural Information Processing Systems. https://doi.org/10.5555/3295222.3295349"
    )


def test_ieee_format():
    text = CitationService.format(TITLE, META, "ieee")
    assert text == (
        'A. Vaswani, N. M. Shazeer, and N. Parmar, "Attention Is All You Need," '
        "Advances in Neural Information Processing Systems, 2017, doi: 10.5555/3295222.3295349."
    )


def test_bibtex_format():
    text = CitationService.format(TITLE, META, "bibtex")
    assert text.startswith("@article{vaswani2017attention,")
    assert "title = {{Attention Is All You Need}}" in text
    assert "author = {Vaswani, A. and Shazeer, N. M. and Parmar, N.}" in text
    assert "doi = {10.5555/3295222.3295349}" in text


def test_ieee_uses_et_al_for_many_authors():
    meta = {"authors": [f"Ada Kisi{i}" for i in range(8)], "year": 2020}
    assert CitationService.format("T", meta, "ieee").startswith("A. Kisi0 et al.")


def test_missing_fields_are_skipped():
    assert CitationService.format("Sadece Baslik", {}, "apa") == "(t.y.). Sadece Baslik."
    assert CitationService.format("Sadece Baslik", {}, "ieee") == '"Sadece Baslik,".'


def test_single_author_and_bibtex_key_without_year():
    text = CitationService.format("The Theory", {"authors": ["Çağla Öz"]}, "bibtex")
    assert text.startswith("@article{ozndtheory,")
    assert "author = {Öz, Ç.}" in text


def test_unsupported_style_raises():
    with pytest.raises(ValueError):
        CitationService.format("T", {}, "chicago")
