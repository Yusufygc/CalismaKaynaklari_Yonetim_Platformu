import re
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

# Depoya kopyalanirken eklenen benzersiz on ek (uuid8_) kullaniciya gosterilmez.
_STORAGE_PREFIX = re.compile(r"^[0-9a-f]{8}_")

# Bilinen platform host'lari -> kisa platform adi. Hem etiketleme
# (services/resource_service.py::_url_tag_names) hem de kart/detay
# panelindeki alan adi rozeti (format_display_url) bu tek listeyi kullanir.
PLATFORM_NAMES = {
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "linkedin.com": "linkedin",
    "instagram.com": "instagram",
    "github.com": "github",
    "x.com": "twitter",
    "twitter.com": "twitter",
    "medium.com": "medium",
    "substack.com": "substack",
    "reddit.com": "reddit",
}


def _match_platform_name(host: str) -> str | None:
    for suffix, platform_name in PLATFORM_NAMES.items():
        if host == suffix or host.endswith(f".{suffix}"):
            return platform_name
    return None


# Otomatik kategori tespitinde platform adinin gorunen (baslik harfli) hali.
_AUTO_CATEGORY_DISPLAY_NAMES = {
    "youtube": "YouTube",
    "instagram": "Instagram",
    "linkedin": "LinkedIn",
    "github": "GitHub",
    "twitter": "Twitter",
    "medium": "Medium",
    "substack": "Substack",
    "reddit": "Reddit",
}

# Akademik/makale barindiran bilinen host'lar -> "Makale" kategorisi.
_ACADEMIC_HOSTS = {
    "doi.org",
    "arxiv.org",
    "scholar.google.com",
    "researchgate.net",
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "sciencedirect.com",
    "springer.com",
    "ieee.org",
    "ieeexplore.ieee.org",
    "jstor.org",
    "dl.acm.org",
    "acm.org",
    "openalex.org",
}


def detect_category_name(url: str | None) -> str | None:
    """URL'den otomatik kategori adi cikarir: 'YouTube', 'Instagram',
    'LinkedIn', 'Makale' (PDF/akademik kaynaklar), veya genel siteler icin
    'Web'. Kullanici formda elle kategori secmediyse (`category_id` bos)
    kaynak eklenirken kullanilir -- kullanicinin elle sectigi kategoriyi
    hicbir zaman ezmez (bkz. services/resource_service.py::add_new_resource).
    """
    if not url:
        return None

    parsed = urlparse(url)

    if parsed.scheme == "file":
        return "Makale" if parsed.path.lower().endswith(".pdf") else None

    if parsed.scheme not in ("http", "https"):
        return None

    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return None

    if host in _ACADEMIC_HOSTS or parsed.path.lower().endswith(".pdf"):
        return "Makale"

    platform = _match_platform_name(host)
    if platform:
        return _AUTO_CATEGORY_DISPLAY_NAMES.get(platform, platform.capitalize())

    return "Web"


def format_display_url(url: str) -> str:
    """URL'yi kisa/okunur bir bicime cevirir: sema, 'www.' ve yol/sorgu atilir.

    Detay panelindeki URL butonunun uzun ham linki degil, sadece alan adini
    (ornegin 'github.com') gostermesi icin kullanilir; tam URL tooltip'te
    ve tiklandiginda acilan tarayicida korunur.

    `file://` URI'leri (yerel PDF ice aktarimlari) icin hostname yok --
    onun yerine dosya adi gosterilir.

    Bilinen platformlarda (youtube.com/youtu.be gibi ayni platformun
    birden fazla host'u olabildigi durumlarda) ham host yerine kisa
    platform adi gosterilir (orn. 'youtu.be' -> 'youtube').
    """
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return _STORAGE_PREFIX.sub("", Path(url2pathname(unquote(parsed.path))).name)

    host = (parsed.hostname or url).lower()
    if host.startswith("www."):
        host = host[4:]

    return _match_platform_name(host) or host
