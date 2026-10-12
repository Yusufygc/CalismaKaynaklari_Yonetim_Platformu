import socket

import pytest


@pytest.fixture()
def fake_dns(monkeypatch):
    """DNS cozumlemesini sahteler: testler gercek ag/DNS'e bagimli olmasin."""

    def _fake_getaddrinfo(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr("core.net_utils.socket.getaddrinfo", _fake_getaddrinfo)
