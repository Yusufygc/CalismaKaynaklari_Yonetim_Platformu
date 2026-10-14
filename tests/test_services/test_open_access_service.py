import requests

from services.open_access_service import OpenAccessService


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _patch_get(monkeypatch, response=None, error=None):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if error:
            raise error
        return response

    monkeypatch.setattr("services.open_access_service.requests.get", fake_get)
    return calls


def test_the_best_open_location_pdf_wins_and_the_doi_is_normalized_and_quoted(monkeypatch):
    calls = _patch_get(monkeypatch, FakeResponse({"best_oa_location": {"pdf_url": "https://arxiv.org/pdf/1207.0203"}, "locations": []}))

    url = OpenAccessService().find_pdf_url("https://doi.org/10.1016/J.Future.2013.01.010")

    assert url == "https://arxiv.org/pdf/1207.0203"
    assert calls[0][0] == "https://api.openalex.org/works/doi:10.1016/j.future.2013.01.010"
    assert calls[0][1]["timeout"] > 0


def test_other_open_locations_are_used_when_there_is_no_best_pdf(monkeypatch):
    work = {
        "best_oa_location": {"pdf_url": None},
        "locations": [
            {"is_oa": False, "pdf_url": "https://yayinci.example/kapali.pdf"},
            {"is_oa": True, "pdf_url": None},
            {"is_oa": True, "pdf_url": "http://repo.example/acik.pdf"},
        ],
    }
    _patch_get(monkeypatch, FakeResponse(work))

    assert OpenAccessService().find_pdf_url("10.1234/abc") == "http://repo.example/acik.pdf"


def test_nothing_is_returned_without_an_open_copy_a_bad_doi_a_bad_status_or_a_network_error(monkeypatch):
    _patch_get(monkeypatch, FakeResponse({"best_oa_location": None, "locations": [{"is_oa": False, "pdf_url": "https://x.example/a.pdf"}]}))
    assert OpenAccessService().find_pdf_url("10.1234/abc") is None

    calls = _patch_get(monkeypatch, FakeResponse({}))
    assert OpenAccessService().find_pdf_url("doi degil") is None and OpenAccessService().find_pdf_url(None) is None
    assert calls == []  # gecersiz DOI icin ag istegi atilmaz

    _patch_get(monkeypatch, FakeResponse({}, status_code=404))
    assert OpenAccessService().find_pdf_url("10.1234/abc") is None
    _patch_get(monkeypatch, FakeResponse(ValueError("bozuk json")))
    assert OpenAccessService().find_pdf_url("10.1234/abc") is None
    _patch_get(monkeypatch, error=requests.ConnectionError("ag yok"))
    assert OpenAccessService().find_pdf_url("10.1234/abc") is None


def test_a_non_http_pdf_address_is_never_returned(monkeypatch):
    _patch_get(monkeypatch, FakeResponse({"best_oa_location": {"pdf_url": "file:///c:/gizli.pdf"}, "locations": [{"is_oa": True, "pdf_url": "ftp://x/a.pdf"}]}))
    assert OpenAccessService().find_pdf_url("10.1234/abc") is None


def test_without_a_doi_the_exact_title_match_provides_the_open_copy(monkeypatch):
    results = {"results": [
        {"title": "Baska Bir Makale Hakkinda Uzun Baslik", "best_oa_location": {"pdf_url": "https://yanlis.example/a.pdf"}},
        {"title": "Deep Learning: A Survey of Methods!", "best_oa_location": {"pdf_url": "https://dogru.example/b.pdf"}},
    ]}
    calls = _patch_get(monkeypatch, FakeResponse(results))

    url = OpenAccessService().find_pdf_url(None, "deep learning - a survey of methods")

    assert url == "https://dogru.example/b.pdf"
    assert calls[0][0] == "https://api.openalex.org/works" and calls[0][1]["params"]["search"] == "deep learning - a survey of methods"


def test_the_title_lookup_falls_back_after_a_doi_without_copy_and_skips_short_or_unmatched_titles(monkeypatch):
    responses = iter([FakeResponse({"best_oa_location": None, "locations": []}), FakeResponse({"results": [{"title": "Ayni Baslik Burada Var", "best_oa_location": {"pdf_url": "https://x.example/a.pdf"}}]})])
    monkeypatch.setattr("services.open_access_service.requests.get", lambda url, **kw: next(responses))
    assert OpenAccessService().find_pdf_url("10.1234/abc", "Ayni baslik burada var") == "https://x.example/a.pdf"

    calls = _patch_get(monkeypatch, FakeResponse({"results": []}))
    assert OpenAccessService().find_pdf_url(None, "Kisa") is None and calls == []  # kisa baslik aranmaz
    _patch_get(monkeypatch, FakeResponse({"results": [{"title": "Tamamen Farkli Bir Makale Basligi", "best_oa_location": {"pdf_url": "https://x.example/a.pdf"}}]}))
    assert OpenAccessService().find_pdf_url(None, "Aranan Uzun Bir Makale Basligi") is None
