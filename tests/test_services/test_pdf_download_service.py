import socket

import pytest
import requests

from services.pdf_download_service import looks_like_remote_pdf, stream_fetch

pytestmark = pytest.mark.usefixtures("fake_dns")


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


class _Response:
    is_redirect = False
    headers: dict = {}

    def raise_for_status(self) -> None:
        return None


def test_stream_fetch_requests_with_stream_enabled(monkeypatch):
    seen = {}

    def _get(url, **kwargs):
        seen.update(kwargs)
        return _Response()

    monkeypatch.setattr("services.pdf_download_service.requests.get", _get)

    assert stream_fetch("https://example.com/x.pdf") is not None
    assert seen["stream"] is True and seen["allow_redirects"] is False


def test_stream_fetch_propagates_network_errors(monkeypatch):
    def _boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr("services.pdf_download_service.requests.get", _boom)

    with pytest.raises(requests.ConnectionError):
        stream_fetch("https://example.com/x.pdf")


def test_stream_fetch_blocks_internal_addresses(monkeypatch):
    monkeypatch.setattr(
        "core.net_utils.socket.getaddrinfo",
        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )

    def _refuse(*a, **k):
        raise AssertionError("ic ag'a istek atilmamali")

    monkeypatch.setattr("services.pdf_download_service.requests.get", _refuse)

    assert stream_fetch("http://internal.example/x.pdf") is None
