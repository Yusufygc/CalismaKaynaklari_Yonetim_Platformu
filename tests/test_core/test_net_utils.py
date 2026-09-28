import socket

import pytest

from core import net_utils
from core.net_utils import is_blocked_host


def _fake_getaddrinfo(*ip_addresses):
    def _impl(host, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0)) for ip in ip_addresses
        ]

    return _impl


def test_allows_public_ipv4(monkeypatch):
    monkeypatch.setattr(net_utils.socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))

    assert is_blocked_host("https://example.com/") is False


def test_allows_public_ipv6(monkeypatch):
    monkeypatch.setattr(net_utils.socket, "getaddrinfo", _fake_getaddrinfo("2606:2800:220:1:248:1893:25c8:1946"))

    assert is_blocked_host("https://example.com/") is False


@pytest.mark.parametrize(
    ("resolved_ip",),
    [
        ("127.0.0.1",),  # loopback
        ("10.0.0.5",),  # private (RFC1918)
        ("172.16.0.1",),  # private (RFC1918)
        ("192.168.1.1",),  # private (RFC1918)
        ("169.254.169.254",),  # link-local (bulut metadata servisi)
        ("240.0.0.1",),  # reserved
        ("224.0.0.1",),  # multicast
        ("::1",),  # IPv6 loopback
    ],
)
def test_blocks_internal_and_special_use_addresses(monkeypatch, resolved_ip):
    monkeypatch.setattr(net_utils.socket, "getaddrinfo", _fake_getaddrinfo(resolved_ip))

    assert is_blocked_host("http://internal.example/") is True


def test_blocks_when_any_resolved_address_is_internal(monkeypatch):
    """DNS rebinding senaryosu: birden fazla A kaydindan biri bile ic ag ise engellenmeli."""

    def _multi(host, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
        ]

    monkeypatch.setattr(net_utils.socket, "getaddrinfo", _multi)

    assert is_blocked_host("http://mixed.example/") is True


def test_blocks_when_dns_resolution_fails(monkeypatch):
    def _raise_gaierror(host, *args, **kwargs):
        raise socket.gaierror("cozumlenemedi")

    monkeypatch.setattr(net_utils.socket, "getaddrinfo", _raise_gaierror)

    assert is_blocked_host("http://does-not-resolve.invalid/") is True


def test_blocks_when_url_has_no_hostname(monkeypatch):
    def _refuse_dns_call(*args, **kwargs):
        raise AssertionError("hostname yoksa DNS'e hic gidilmemeli")

    monkeypatch.setattr(net_utils.socket, "getaddrinfo", _refuse_dns_call)

    assert is_blocked_host("not-a-url") is True
    assert is_blocked_host("") is True
