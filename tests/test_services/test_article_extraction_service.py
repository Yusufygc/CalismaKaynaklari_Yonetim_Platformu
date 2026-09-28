import socket

import pytest

from services.article_extraction_service import ArticleExtractionService


@pytest.fixture(autouse=True)
def _fake_dns(monkeypatch):
    """DNS cozumlemesini sahteler: testler gercek ag/DNS'e bagimli olmasin."""

    def _fake_getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr("core.net_utils.socket.getaddrinfo", _fake_getaddrinfo)


class _Response:
    is_redirect = False

    def __init__(self, text: str = "", content: bytes = b"", url: str = "https://example.com/article") -> None:
        self.text = text
        self.content = content if content else text.encode("utf-8")
        self.url = url
        self.headers: dict = {}

    def raise_for_status(self) -> None:
        return None


class _RedirectResponse:
    is_redirect = True

    def __init__(self, location: str) -> None:
        self.headers = {"Location": location}

    def raise_for_status(self) -> None:
        return None


def test_extract_full_text_returns_extracted_html(monkeypatch):
    monkeypatch.setattr(
        "services.article_extraction_service.requests.get",
        lambda *args, **kwargs: _Response("<html><body><h1>B</h1><p>Metin</p></body></html>"),
    )
    monkeypatch.setattr(
        "services.article_extraction_service.trafilatura.extract",
        lambda downloaded, **kwargs: "<h1>Baslik</h1><p>Makale govde metni.</p>",
    )

    result = ArticleExtractionService().extract_full_text("https://example.com/article")

    assert result == "<h1>Baslik</h1><p>Makale govde metni.</p>"


def test_extract_full_text_requests_html_output(monkeypatch):
    captured = {}

    def _fake_extract(downloaded, **kwargs):
        captured.update(kwargs)
        return "<p>Makale govde metni.</p>"

    monkeypatch.setattr(
        "services.article_extraction_service.requests.get",
        lambda *args, **kwargs: _Response("<html><body><p>x</p></body></html>"),
    )
    monkeypatch.setattr("services.article_extraction_service.trafilatura.extract", _fake_extract)

    ArticleExtractionService().extract_full_text("https://example.com/article")

    assert captured["output_format"] == "html"
    assert captured["include_formatting"] is True


def test_extract_full_text_passes_configured_timeout(monkeypatch):
    captured = {}

    def _fake_get(url, **kwargs):
        captured.update(kwargs)
        return _Response("<html><body><p>x</p></body></html>")

    monkeypatch.setattr("services.article_extraction_service.requests.get", _fake_get)
    monkeypatch.setattr(
        "services.article_extraction_service.trafilatura.extract",
        lambda downloaded, **kwargs: "<p>Makale govde metni.</p>",
    )

    ArticleExtractionService().extract_full_text("https://example.com/article")

    assert captured["timeout"] == 10


def test_extract_full_text_returns_none_on_http_error(monkeypatch):
    import requests

    class _FailingResponse(_Response):
        def raise_for_status(self):
            raise requests.HTTPError("404")

    monkeypatch.setattr(
        "services.article_extraction_service.requests.get",
        lambda *args, **kwargs: _FailingResponse(),
    )

    assert ArticleExtractionService().extract_full_text("https://example.com/article") is None


def test_extract_full_text_returns_none_on_exception(monkeypatch):
    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("services.article_extraction_service.requests.get", _raise)

    assert ArticleExtractionService().extract_full_text("https://example.com/article") is None


def test_extract_full_text_blocks_internal_addresses(monkeypatch):
    def _refuse_network_call(*args, **kwargs):
        raise AssertionError("requests.get cagrilmamali - SSRF korumasi engellemeliydi")

    monkeypatch.setattr("services.article_extraction_service.requests.get", _refuse_network_call)
    monkeypatch.setattr(
        "core.net_utils.socket.getaddrinfo",
        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )

    assert ArticleExtractionService().extract_full_text("http://internal.example/") is None


def test_extract_full_text_follows_redirect_and_rechecks_ssrf(monkeypatch):
    calls = []

    def _fake_get(url, **kwargs):
        calls.append(url)
        if url == "https://example.com/start":
            return _RedirectResponse("https://example.com/final")
        return _Response("<html><body><p>x</p></body></html>", url=url)

    monkeypatch.setattr("services.article_extraction_service.requests.get", _fake_get)
    monkeypatch.setattr(
        "services.article_extraction_service.trafilatura.extract",
        lambda downloaded, **kwargs: "<p>Makale govde metni.</p>",
    )

    result = ArticleExtractionService().extract_full_text("https://example.com/start")

    assert result == "<p>Makale govde metni.</p>"
    assert calls == ["https://example.com/start", "https://example.com/final"]


def test_extract_full_text_extracts_pdf_pages_with_page_numbers(monkeypatch):
    class _FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class _FakeReader:
        def __init__(self, _stream) -> None:
            self.pages = [_FakePage("Birinci   sayfa   metni."), _FakePage("")]

    monkeypatch.setattr("services.article_extraction_service.PdfReader", _FakeReader)
    monkeypatch.setattr(
        "services.article_extraction_service.requests.get",
        lambda *args, **kwargs: _Response(content=b"%PDF-1.4 fake pdf bytes"),
    )

    result = ArticleExtractionService().extract_full_text("https://example.com/paper.pdf")

    assert result == "<h3>Sayfa 1</h3><p>Birinci sayfa metni.</p>"


def test_extract_full_text_detects_pdf_from_url_extension(monkeypatch):
    captured = {}

    class _FakePage:
        def extract_text(self) -> str:
            return "Metin"

    class _FakeReader:
        def __init__(self, _stream) -> None:
            captured["used"] = True
            self.pages = [_FakePage()]

    monkeypatch.setattr("services.article_extraction_service.PdfReader", _FakeReader)
    monkeypatch.setattr(
        "services.article_extraction_service.requests.get",
        lambda *args, **kwargs: _Response(
            content=b"not-actually-pdf-bytes-but-url-ends-in-pdf",
            url="https://example.com/paper.pdf",
        ),
    )

    ArticleExtractionService().extract_full_text("https://example.com/paper.pdf")

    assert captured.get("used") is True


def test_extract_full_text_reads_local_pdf_without_network(tmp_path, monkeypatch):
    class _FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class _FakeReader:
        def __init__(self, _stream) -> None:
            self.pages = [_FakePage("Yerel sayfa metni.")]

    def _refuse_network_call(*args, **kwargs):
        raise AssertionError("Yerel PDF icin ag istegi atilmamali")

    monkeypatch.setattr("services.article_extraction_service.PdfReader", _FakeReader)
    monkeypatch.setattr("services.article_extraction_service.requests.get", _refuse_network_call)

    pdf_path = tmp_path / "makale.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake local pdf bytes")

    result = ArticleExtractionService().extract_full_text(pdf_path.as_uri())

    assert result == "<h3>Sayfa 1</h3><p>Yerel sayfa metni.</p>"


def test_extract_full_text_returns_none_when_local_pdf_missing(tmp_path):
    missing_path = tmp_path / "yok.pdf"

    result = ArticleExtractionService().extract_full_text(missing_path.as_uri())

    assert result is None
