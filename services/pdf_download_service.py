from functools import partial
from urllib.parse import urlparse

import requests

from core.net_utils import safe_http_get

_TIMEOUT_SECONDS = 30
_MAX_REDIRECTS = 5
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def looks_like_remote_pdf(url: str | None) -> bool:
    """URL'nin dogrudan bir PDF'e isaret ettigini tahmin eder (indirmeden once).

    Her http(s) sayfasi icin indirme denemek israf olur; sadece belirgin
    PDF desenleri (.pdf uzantisi, arxiv.org/pdf/, /pdf/ yol parcasi) denenir.
    """
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    path = parsed.path.lower()
    return path.endswith(".pdf") or "/pdf/" in path or path.startswith("/pdf")


def stream_fetch(url: str) -> requests.Response | None:
    """Web PDF'ini akis halinde (`stream=True`) getirir; her yonlendirmede hedef SSRF kontrolunden gecer.
    Reddedilirse (ic ag / yonlendirme siniri) None doner. Govdeyi okumak `pdfkit.infra.downloader`in isidir.

    `QtQuick.Pdf.PdfDocument` ag uzerinden acamiyor, yalnizca yerel dosya aciyor -- bu yuzden web PDF'leri once
    pdfkit deposuna indirilir."""
    return safe_http_get(
        url,
        timeout=_TIMEOUT_SECONDS,
        max_redirects=_MAX_REDIRECTS,
        headers=_HEADERS,
        requester=partial(requests.get, stream=True),
    )
