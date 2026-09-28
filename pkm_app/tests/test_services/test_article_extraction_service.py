import socket

import pytest

from pkm_app.services.article_extraction_service import ArticleExtractionService


@pytest.fixture(autouse=True)
def _fake_dns(monkeypatch):
    """DNS cozumlemesini sahteler: testler gercek ag/DNS'e bagimli olmasin."""

    def _fake_getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr("pkm_app.core.net_utils.socket.getaddrinfo", _fake_getaddrinfo)


def test_extract_full_text_returns_extracted_content(monkeypatch):
    monkeypatch.setattr(
        "pkm_app.services.article_extraction_service.trafilatura.fetch_url",
        lambda url, **kwargs: "<html>...</html>",
    )
    monkeypatch.setattr(
        "pkm_app.services.article_extraction_service.trafilatura.extract",
        lambda downloaded, **kwargs: "Makale govde metni.",
    )

    result = ArticleExtractionService().extract_full_text("https://example.com/article")

    assert result == "Makale govde metni."


def test_extract_full_text_passes_configured_timeout(monkeypatch):
    captured = {}

    def _fake_fetch_url(url, **kwargs):
        captured.update(kwargs)
        return "<html>...</html>"

    monkeypatch.setattr(
        "pkm_app.services.article_extraction_service.trafilatura.fetch_url",
        _fake_fetch_url,
    )
    monkeypatch.setattr(
        "pkm_app.services.article_extraction_service.trafilatura.extract",
        lambda downloaded, **kwargs: "Makale govde metni.",
    )

    ArticleExtractionService().extract_full_text("https://example.com/article")

    assert "config" in captured
    assert captured["config"].getint("DEFAULT", "DOWNLOAD_TIMEOUT") == 10


def test_extract_full_text_returns_none_when_fetch_fails(monkeypatch):
    monkeypatch.setattr(
        "pkm_app.services.article_extraction_service.trafilatura.fetch_url",
        lambda url, **kwargs: None,
    )

    assert ArticleExtractionService().extract_full_text("https://example.com/article") is None


def test_extract_full_text_returns_none_on_exception(monkeypatch):
    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "pkm_app.services.article_extraction_service.trafilatura.fetch_url", _raise
    )

    assert ArticleExtractionService().extract_full_text("https://example.com/article") is None


def test_extract_full_text_blocks_internal_addresses(monkeypatch):
    def _refuse_network_call(*args, **kwargs):
        raise AssertionError("trafilatura cagrilmamali - SSRF korumasi engellemeliydi")

    monkeypatch.setattr(
        "pkm_app.services.article_extraction_service.trafilatura.fetch_url",
        _refuse_network_call,
    )
    monkeypatch.setattr(
        "pkm_app.core.net_utils.socket.getaddrinfo",
        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )

    assert ArticleExtractionService().extract_full_text("http://internal.example/") is None
