import re
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from core.logger import log
from core.net_utils import safe_http_get

_TIMEOUT_SECONDS = 30
_MAX_REDIRECTS = 5
_MAX_BYTES = 100 * 1024 * 1024
_PDF_MAGIC = b"%PDF-"
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')
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


class PdfDownloadService:
    """Web'deki bir PDF'i yerel depolama dizinine indirir (native okuyucu icin).

    `QtQuick.Pdf.PdfDocument` ag uzerinden acamiyor, sadece yerel dosya
    aciyor -- bu yuzden web PDF'leri once diske alinip `file://` gibi
    davranir. Indirilen icerik %PDF- imzasiyla dogrulanir (HTML hata sayfasi
    yanlislikla PDF diye kaydedilmez).
    """

    def download(self, url: str, dest_dir: Path) -> Path | None:
        try:
            response = safe_http_get(
                url,
                timeout=_TIMEOUT_SECONDS,
                max_redirects=_MAX_REDIRECTS,
                headers=_HEADERS,
                requester=requests.get,
            )
        except requests.RequestException as exc:
            log.warning("PDF indirilemedi: %s - %s", url, exc)
            return None
        if response is None:
            log.warning("PDF indirme reddedildi (ic ag/yonlendirme siniri): %s", url)
            return None

        content = response.content
        if content[:5] != _PDF_MAGIC:
            log.info("URL bir PDF degil (imza uyusmuyor): %s", url)
            return None
        if len(content) > _MAX_BYTES:
            log.warning("PDF cok buyuk (%d bayt), indirme iptal: %s", len(content), url)
            return None

        name = Path(unquote(urlparse(response.url).path)).name
        # Path.stem, "1706.03762" gibi arXiv id'lerinde ".03762"yi uzanti sanip kirpar.
        stem = (name[:-4] if name.lower().endswith(".pdf") else name) or "makale"
        safe_stem = _UNSAFE_FILENAME_CHARS.sub("_", stem)[:60]
        dest = (dest_dir / f"{uuid.uuid4().hex[:8]}_{safe_stem}.pdf").resolve()
        try:
            dest.write_bytes(content)
        except OSError as exc:
            log.warning("PDF diske yazilamadi: %s - %s", dest, exc)
            return None
        return dest
