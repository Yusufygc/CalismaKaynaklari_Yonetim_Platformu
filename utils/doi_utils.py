import re

_DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
_DOI_IN_URL = re.compile(r"doi\.org/(10\.\d{4,9}/[^\s?#]+)", re.IGNORECASE)


def normalize_doi(doi: str | None) -> str:
    """'https://doi.org/10.1/ABC' -> '10.1/abc' (karsilastirma anahtari; bos ise '')."""
    if not doi:
        return ""
    return _DOI_PREFIX.sub("", doi.strip()).strip().lower()


def doi_from_url(url: str | None) -> str | None:
    """`doi.org` baglantisindan DOI'yi cikarir; yoksa None."""
    match = _DOI_IN_URL.search(url or "")
    return match.group(1) if match else None
