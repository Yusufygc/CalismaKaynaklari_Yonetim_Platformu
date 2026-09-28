import ipaddress
import socket
from urllib.parse import urljoin, urlparse
from typing import Callable, Any
import requests


def is_blocked_host(url: str) -> bool:
    """Ic ag / loopback / link-local adreslere istek atilmasini engeller (SSRF)."""
    hostname = urlparse(url).hostname
    if not hostname:
        return True
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
    except socket.gaierror:
        return True
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
    return False


def safe_http_get(
    url: str,
    *,
    timeout: int = 5,
    max_redirects: int = 5,
    headers: dict | None = None,
    requester: Callable[..., Any] | None = None,
) -> requests.Response | None:
    """Her yönlendirme adımında hedefi is_blocked_host ile doğrular (SSRF koruması)."""
    if requester is None:
        requester = requests.get

    current_url = url
    for _ in range(max_redirects + 1):
        if is_blocked_host(current_url):
            return None
        response = requester(
            current_url,
            headers=headers,
            timeout=timeout,
            allow_redirects=False,
        )
        if response.is_redirect:
            location = response.headers.get("Location")
            if not location:
                return None
            current_url = urljoin(current_url, location)
            continue
        response.raise_for_status()
        return response
    return None
