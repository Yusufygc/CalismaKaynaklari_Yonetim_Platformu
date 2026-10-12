import pytest

from pdfkit.domain.errors import DownloadError, TooLargeError
from pdfkit.infra.downloader import download_to_temp


class FakeStream:
    def __init__(self, chunks, headers=None):
        self._chunks = chunks
        self.headers = headers or {}
        self.closed = False

    def iter_content(self, chunk_size):
        yield from self._chunks

    def close(self):
        self.closed = True


def _download(tmp_path, stream, max_bytes=1000):
    return download_to_temp("https://x.org/a.pdf", fetch=lambda url: stream, temp_dir=tmp_path, max_bytes=max_bytes)


def test_streams_to_temp_file_and_closes_response(tmp_path):
    stream = FakeStream([b"%PDF-1.4 ", b"govde"])

    path = _download(tmp_path, stream)

    assert path.read_bytes() == b"%PDF-1.4 govde"
    assert stream.closed


def test_rejects_non_pdf_and_leaves_no_temp_file(tmp_path):
    with pytest.raises(DownloadError):
        _download(tmp_path, FakeStream([b"<html>404</html>"]))
    assert list(tmp_path.iterdir()) == []


def test_size_limit_is_enforced_while_streaming(tmp_path):
    chunks = [b"%PDF-1.4 " + b"x" * 50] + [b"y" * 50] * 30  # Content-Length bildirilmiyor
    with pytest.raises(TooLargeError):
        _download(tmp_path, FakeStream(chunks), max_bytes=500)
    assert list(tmp_path.iterdir()) == []


def test_declared_content_length_over_limit_is_rejected_before_reading(tmp_path):
    stream = FakeStream([b"%PDF-1.4 x"], headers={"Content-Length": "999999"})
    with pytest.raises(TooLargeError):
        _download(tmp_path, stream, max_bytes=500)
    assert stream.closed


def test_blocked_host_returns_download_error(tmp_path):
    with pytest.raises(DownloadError):
        download_to_temp("http://internal/x.pdf", fetch=lambda url: None, temp_dir=tmp_path, max_bytes=10)


def test_empty_body_is_an_error(tmp_path):
    with pytest.raises(DownloadError):
        _download(tmp_path, FakeStream([]))
