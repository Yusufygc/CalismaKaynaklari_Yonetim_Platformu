import socket

import pytest

from services.pdf_download_service import PdfDownloadService, looks_like_remote_pdf


@pytest.fixture(autouse=True)
def _fake_dns(monkeypatch):
    monkeypatch.setattr(
        "core.net_utils.socket.getaddrinfo",
        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )


class _Response:
    is_redirect = False

    def __init__(self, content: bytes, url: str = "https://example.com/papers/attention.pdf") -> None:
        self.content = content
        self.url = url
        self.headers: dict = {}

    def raise_for_status(self) -> None:
        return None


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://arxiv.org/pdf/1706.03762", True),
        ("https://example.com/files/paper.PDF", True),
        ("https://example.com/pdf/12345", True),
        ("https://example.com/article/12345", False),
        ("https://doi.org/10.1000/xyz", False),
        ("file:///C:/x.pdf", False),
        (None, False),
        ("", False),
    ],
)
def test_looks_like_remote_pdf(url, expected):
    assert looks_like_remote_pdf(url) is expected


def test_download_saves_valid_pdf(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "services.pdf_download_service.requests.get",
        lambda *a, **k: _Response(b"%PDF-1.7 fake pdf body"),
    )

    path = PdfDownloadService().download("https://example.com/papers/attention.pdf", tmp_path)

    assert path is not None
    assert path.parent == tmp_path.resolve()
    assert path.name.endswith("_attention.pdf")
    assert path.read_bytes().startswith(b"%PDF-")


def test_download_rejects_html_masquerading_as_pdf(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "services.pdf_download_service.requests.get",
        lambda *a, **k: _Response(b"<html>404 not found</html>"),
    )

    assert PdfDownloadService().download("https://example.com/x.pdf", tmp_path) is None
    assert list(tmp_path.iterdir()) == []


def test_download_returns_none_on_network_error(monkeypatch, tmp_path):
    import requests

    def _boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr("services.pdf_download_service.requests.get", _boom)

    assert PdfDownloadService().download("https://example.com/x.pdf", tmp_path) is None


def test_download_blocks_internal_addresses(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "core.net_utils.socket.getaddrinfo",
        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )

    def _refuse(*a, **k):
        raise AssertionError("ic ag'a istek atilmamali")

    monkeypatch.setattr("services.pdf_download_service.requests.get", _refuse)

    assert PdfDownloadService().download("http://internal.example/x.pdf", tmp_path) is None
