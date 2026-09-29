import html
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

import requests
import trafilatura
from pypdf import PdfReader

from core.logger import log
from core.net_utils import is_blocked_host, safe_http_get
from utils.text_utils import sanitize_utf8

_TIMEOUT_SECONDS = 10
_MAX_REDIRECTS = 5
_PDF_MAGIC = b"%PDF-"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def _looks_like_pdf(url: str, content: bytes) -> bool:
    return content[:5] == _PDF_MAGIC or url.lower().split("?")[0].endswith(".pdf")


def _extract_pdf_html(content: bytes) -> str | None:
    """PDF sayfalarini sayfa-numarali HTML'e cevirir (<h3>Sayfa N</h3><p>...</p>).

    Sayfa ici satir kirilimlari (print-genisligi kaynakli) paragraf siniri
    sayilmiyor -- tum sayfa metni tek paragrafta normalize ediliyor. PDF'ten
    guvenilir paragraf tespiti zor oldugu icin bilincli bir basitlestirme.
    """
    reader = PdfReader(BytesIO(content))
    parts = []
    for i, page in enumerate(reader.pages, start=1):
        text = sanitize_utf8(" ".join((page.extract_text() or "").split()))
        if text:
            parts.append(f"<h3>Sayfa {i}</h3><p>{html.escape(text)}</p>")
    return "".join(parts) or None


class ArticleExtractionService:
    """Web makalelerinin (HTML veya PDF) govde metnini HTML olarak cikarir
    (okuyucu sayfasi icin).

    ScraperService'ten ayri tutulur: ScraperService hafif og:meta scraping
    yapar, burada ya trafilatura'nin boilerplate-temizleme sezgiseli ya da
    (PDF'lerde) pypdf calisir -- farkli sorumluluk, farkli hata modu (None doner).
    """

    def extract_full_text(self, url: str) -> str | None:
        """Makale govdesini semantik HTML olarak dondurur.

        HTML kaynaklarda gercek yapi korunur (h1/p/blockquote/strong/i,
        `output_format="html"`). URL dogrudan bir PDF'e isaret ediyorsa
        (dosya imzasi veya `.pdf` uzantisi) pypdf ile sayfa-numarali HTML
        uretilir (bkz. `_extract_pdf_html`).

        `file://` URI'leri (yerel PDF ice aktarimlari) icin ag/SSRF mantigina
        hic girilmez -- diskten dogrudan okunur (bkz. `_extract_local_pdf`).
        """
        if urlparse(url).scheme == "file":
            return self._extract_local_pdf(url)

        if is_blocked_host(url):
            log.warning("URL ic ag/loopback adresine cozumlendigi icin reddedildi: %s", url)
            return None
        try:
            response = self._safe_get(url)
            if response is None:
                return None

            if _looks_like_pdf(response.url, response.content):
                return _extract_pdf_html(response.content)

            return trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False,
                output_format="html",
                include_formatting=True,
            )
        except Exception as exc:
            log.warning("Tam metin cikarilamadi: %s - %s", url, exc)
            return None

    def _extract_local_pdf(self, file_url: str) -> str | None:
        """Yerel diskteki bir PDF'i okur (ag istegi yok, SSRF kontrolu gerekmez)."""
        try:
            local_path = Path(url2pathname(unquote(urlparse(file_url).path)))
            content = local_path.read_bytes()
        except OSError as exc:
            log.warning("Yerel PDF okunamadi: %s - %s", file_url, exc)
            return None
        return _extract_pdf_html(content)

    def _safe_get(self, url: str) -> requests.Response | None:
        """Her yonlendirme adiminda hedefi is_blocked_host ile tekrar dogrular (SSRF)."""
        return safe_http_get(
            url,
            timeout=_TIMEOUT_SECONDS,
            max_redirects=_MAX_REDIRECTS,
            headers=_HEADERS,
            requester=requests.get,
        )
