"""`pkm://open?doc=<sha>&page=<n>&ann=<uid>` derin baglantisi: Obsidian notundan uygulamadaki PDF'e/alintiya gider.

Baglanti disaridan gelir (tarayici, Obsidian, komut satiri) ve guvenilmez girdidir: ayrıştırıcı yalnizca bu bicimi
kabul eder, boyut sinirlari uygular, her seyi dogrular."""
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlsplit

from pdfkit.domain.errors import InvalidLinkError

SCHEME = "pkm"
ACTION = "open"
DOC_PREFIX_LENGTH = 16  # belge SHA-256'sinin baglantidaki hane sayisi
_MAX_LENGTH = 512
_MAX_PAGE = 100_000
_DOC = re.compile(r"[0-9a-f]{8,64}")
_ULID = re.compile(r"[0-9A-HJKMNP-TV-Z]{26}")


@dataclass(frozen=True)
class OpenLink:
    doc: str  # belge SHA-256 on eki (kucuk harfli hex, 8-64 hane)
    page: int | None = None  # 0 tabanli sayfa indeksi
    ann: str | None = None  # alinti (ya da not) uid'si (ULID)


def build_open_link(sha256: str, page: int | None = None, ann_uid: str | None = None) -> str:
    """Belgeyi (isteğe bağlı sayfayı ve alıntıyı) acan baglanti. `page` 0 tabanlidir, baglantida 1 tabanli yazilir."""
    params = {"doc": sha256.lower()[:DOC_PREFIX_LENGTH]}
    if page is not None:
        params["page"] = str(page + 1)
    if ann_uid:
        params["ann"] = ann_uid
    return f"{SCHEME}://{ACTION}?{urlencode(params)}"


def parse_open_link(url: str) -> OpenLink:
    """Gecerli bir `pkm://open?...` baglantisini cozer; aksi halde `InvalidLinkError`."""
    if not isinstance(url, str) or len(url) > _MAX_LENGTH:
        raise InvalidLinkError("Baglanti gecersiz ya da cok uzun.")
    parts = urlsplit(url.strip())
    if parts.scheme != SCHEME or parts.netloc != ACTION or parts.path not in ("", "/"):
        raise InvalidLinkError("Desteklenmeyen baglanti.")
    query = parse_qs(parts.query, keep_blank_values=True, strict_parsing=False)
    if set(query) - {"doc", "page", "ann"} or any(len(values) != 1 for values in query.values()):
        raise InvalidLinkError("Baglanti parametreleri gecersiz.")
    doc = query.get("doc", [""])[0].lower()
    if not _DOC.fullmatch(doc):
        raise InvalidLinkError("Belge kimligi gecersiz.")
    page = None
    if "page" in query:
        raw = query["page"][0]
        if not (raw.isascii() and raw.isdigit()) or not 1 <= int(raw) <= _MAX_PAGE:
            raise InvalidLinkError("Sayfa numarasi gecersiz.")
        page = int(raw) - 1
    ann = None
    if "ann" in query:
        ann = query["ann"][0]
        if not _ULID.fullmatch(ann):
            raise InvalidLinkError("Alinti kimligi gecersiz.")
    return OpenLink(doc, page, ann)
