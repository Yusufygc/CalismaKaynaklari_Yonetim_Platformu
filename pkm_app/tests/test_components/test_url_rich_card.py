import socket

import pytest

from pkm_app.ui.components import url_rich_card as url_rich_card_module
from pkm_app.ui.components.url_rich_card import ThumbnailWorker
from pkm_app.core import net_utils


@pytest.fixture(autouse=True)
def _fake_dns(monkeypatch):
    """DNS cozumlemesini sahteler: testler gercek ag/DNS'e bagimli olmasin."""

    def _fake_getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(net_utils.socket, "getaddrinfo", _fake_getaddrinfo)


class _Response:
    is_redirect = False

    def __init__(self, content: bytes) -> None:
        self.content = content
        self.headers: dict = {}

    def raise_for_status(self) -> None:
        return None


class _RedirectResponse:
    is_redirect = True

    def __init__(self, location: str) -> None:
        self.headers = {"Location": location}

    def raise_for_status(self) -> None:
        return None


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


def test_run_emits_finished_with_downloaded_bytes(qapp, monkeypatch):
    calls = {}

    def _fake_get(url, *args, **kwargs):
        calls["kwargs"] = kwargs
        return _Response(b"fake-image-bytes")

    monkeypatch.setattr(url_rich_card_module.requests, "get", _fake_get)

    worker = ThumbnailWorker("https://example.com/thumb.jpg")
    finished = _capture(worker.signals.finished)
    error = _capture(worker.signals.error)

    worker.run()

    assert finished == [("https://example.com/thumb.jpg", b"fake-image-bytes")]
    assert error == []
    # TLS sertifika dogrulamasi kapatilmamali (varsayilan requests davranisi korunmali).
    assert calls["kwargs"].get("verify", True) is True


def test_run_blocks_internal_address(qapp, monkeypatch):
    def _refuse_network_call(*args, **kwargs):
        raise AssertionError("requests.get cagrilmamali - SSRF korumasi engellemeliydi")

    monkeypatch.setattr(url_rich_card_module.requests, "get", _refuse_network_call)
    monkeypatch.setattr(
        net_utils.socket,
        "getaddrinfo",
        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )

    worker = ThumbnailWorker("http://internal.example/thumb.jpg")
    error = _capture(worker.signals.error)

    worker.run()

    assert len(error) == 1


def test_run_blocks_redirect_to_internal_address(qapp, monkeypatch):
    """og:image URL'si disaridan erisilebilir olup ic ag adresine yonlendirirse indirme durmali."""

    def _fake_get(url, *args, **kwargs):
        if url == "https://external.example/start.jpg":
            return _RedirectResponse("http://internal.example/secret.jpg")
        raise AssertionError("yonlendirme hedefi tekrar dogrulanmadan istek atildi")

    def _fake_getaddrinfo(host, *a, **k):
        if host == "internal.example":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(url_rich_card_module.requests, "get", _fake_get)
    monkeypatch.setattr(net_utils.socket, "getaddrinfo", _fake_getaddrinfo)

    worker = ThumbnailWorker("https://external.example/start.jpg")
    error = _capture(worker.signals.error)

    worker.run()

    assert len(error) == 1
