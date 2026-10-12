import socket

import pytest

from services.article_extraction_service import ArticleExtractionService
from tests.pdf_factory import build_text_pdf, write_text_pdf
from tests.test_services.http_fakes import FakeRedirectResponse, FakeResponse

pytestmark = pytest.mark.usefixtures("fake_dns")


def test_extract_full_text_returns_extracted_html(monkeypatch):
    monkeypatch.setattr(
        "services.article_extraction_service.requests.get",
        lambda *args, **kwargs: FakeResponse("<html><body><h1>B</h1><p>Metin</p></body></html>"),
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
        lambda *args, **kwargs: FakeResponse("<html><body><p>x</p></body></html>"),
    )
    monkeypatch.setattr("services.article_extraction_service.trafilatura.extract", _fake_extract)

    ArticleExtractionService().extract_full_text("https://example.com/article")

    assert captured["output_format"] == "html"
    assert captured["include_formatting"] is True


def test_extract_full_text_passes_configured_timeout(monkeypatch):
    captured = {}

    def _fake_get(url, **kwargs):
        captured.update(kwargs)
        return FakeResponse("<html><body><p>x</p></body></html>")

    monkeypatch.setattr("services.article_extraction_service.requests.get", _fake_get)
    monkeypatch.setattr(
        "services.article_extraction_service.trafilatura.extract",
        lambda downloaded, **kwargs: "<p>Makale govde metni.</p>",
    )

    ArticleExtractionService().extract_full_text("https://example.com/article")

    assert captured["timeout"] == 10


def test_extract_full_text_returns_none_on_http_error(monkeypatch):
    import requests

    class _FailingResponse(FakeResponse):
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
            return FakeRedirectResponse("https://example.com/final")
        return FakeResponse("<html><body><p>x</p></body></html>", url=url)

    monkeypatch.setattr("services.article_extraction_service.requests.get", _fake_get)
    monkeypatch.setattr(
        "services.article_extraction_service.trafilatura.extract",
        lambda downloaded, **kwargs: "<p>Makale govde metni.</p>",
    )

    result = ArticleExtractionService().extract_full_text("https://example.com/start")

    assert result == "<p>Makale govde metni.</p>"
    assert calls == ["https://example.com/start", "https://example.com/final"]


def test_extract_full_text_extracts_pdf_pages_with_page_numbers(monkeypatch):
    monkeypatch.setattr(
        "services.article_extraction_service.requests.get",
        lambda *args, **kwargs: FakeResponse(content=build_text_pdf(["Birinci   sayfa   metni."])),
    )

    result = ArticleExtractionService().extract_full_text("https://example.com/paper.pdf")

    assert result == "<h3>Sayfa 1</h3><p>Birinci sayfa metni.</p>"


def test_extract_full_text_treats_pdf_extension_as_pdf_not_html(monkeypatch):
    """`.pdf` uzantili URL trafilatura'ya (HTML) verilmez; bozuk icerik sessizce None olur."""
    monkeypatch.setattr(
        "services.article_extraction_service.requests.get",
        lambda *args, **kwargs: FakeResponse(
            content=b"not-actually-pdf-bytes-but-url-ends-in-pdf",
            url="https://example.com/paper.pdf",
        ),
    )

    def _must_not_run(*args, **kwargs):
        raise AssertionError("PDF URL'si HTML olarak islenmemeli")

    monkeypatch.setattr("services.article_extraction_service.trafilatura.extract", _must_not_run)

    assert ArticleExtractionService().extract_full_text("https://example.com/paper.pdf") is None


def test_extract_full_text_reads_local_pdf_without_network(tmp_path, monkeypatch):
    def _refuse_network_call(*args, **kwargs):
        raise AssertionError("Yerel PDF icin ag istegi atilmamali")

    monkeypatch.setattr("services.article_extraction_service.requests.get", _refuse_network_call)
    pdf_path = write_text_pdf(tmp_path / "makale.pdf", ["Yerel sayfa metni."])

    result = ArticleExtractionService().extract_full_text(pdf_path.as_uri())

    assert result == "<h3>Sayfa 1</h3><p>Yerel sayfa metni.</p>"


def test_extract_full_text_returns_none_when_local_pdf_missing(tmp_path):
    missing_path = tmp_path / "yok.pdf"

    result = ArticleExtractionService().extract_full_text(missing_path.as_uri())

    assert result is None


def test_extract_full_text_sanitizes_lone_surrogates_from_broken_pdf_fonts(monkeypatch):
    """Bozuk CMap'li subset fontlar (akademik PDF'lerdeki matematik semboller) tek-basina UTF-16 surrogate kod
    noktasi uretebiliyor -- bu SQLite'a yazilirken UnicodeEncodeError ile cokuyordu (bkz. utils/text_utils.py)."""
    monkeypatch.setattr(
        "services.article_extraction_service.extract_page_texts",
        lambda content: ["bozuk font " + chr(0xD835) + " sembolu"],
    )
    monkeypatch.setattr(
        "services.article_extraction_service.requests.get",
        lambda *args, **kwargs: FakeResponse(content=b"%PDF-1.4 fake pdf bytes"),
    )

    result = ArticleExtractionService().extract_full_text("https://example.com/paper.pdf")

    assert result is not None
    result.encode("utf-8")  # UnicodeEncodeError firlatirsa test kirmizi olur
    assert chr(0xD835) not in result
