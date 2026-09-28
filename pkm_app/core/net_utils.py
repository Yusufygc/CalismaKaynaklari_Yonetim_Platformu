import ipaddress
import socket
from urllib.parse import urlparse


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
