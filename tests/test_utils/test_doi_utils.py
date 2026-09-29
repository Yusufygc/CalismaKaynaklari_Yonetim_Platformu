from utils.doi_utils import doi_from_url, normalize_doi


def test_normalize_strips_prefixes_and_lowercases():
    assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalize_doi("http://dx.doi.org/10.1000/abc") == "10.1000/abc"
    assert normalize_doi("doi: 10.1000/ABC ") == "10.1000/abc"


def test_normalize_empty():
    assert normalize_doi(None) == ""
    assert normalize_doi("") == ""


def test_doi_from_url():
    assert doi_from_url("https://doi.org/10.1145/3295222.3295349?x=1") == "10.1145/3295222.3295349"
    assert doi_from_url("https://example.org/paper") is None
    assert doi_from_url(None) is None
