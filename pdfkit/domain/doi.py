import re

_DOI = re.compile(r"10\.\d{4,9}/[^\s\"'<>\]\)\}]+", re.IGNORECASE)
_TRAILING = ".,;:"


def extract_doi(text: str | None) -> str | None:
    """Metindeki ilk DOI'yi kucuk harfle dondurur (sondaki noktalama atilir); yoksa None."""
    if not text:
        return None
    match = _DOI.search(text)
    if match is None:
        return None
    return match.group(0).rstrip(_TRAILING).lower() or None
