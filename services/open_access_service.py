import re
from urllib.parse import quote

import requests

from core.logger import log
from utils.doi_utils import normalize_doi

_API_URL = "https://api.openalex.org/works/doi:"
_TIMEOUT_SECONDS = 10
_DOI = re.compile(r"^10\.\d{4,9}/\S+$")


def _http_url(value: object) -> str | None:
    return value if isinstance(value, str) and value.lower().startswith(("http://", "https://")) else None


class OpenAccessService:
    """DOI'si olan bir makalenin **acik erisimli PDF** kopyasini (yayinci sayfasi robotlara kapali olsa da arXiv,
    kurumsal arsiv, PubMed Central...) OpenAlex'ten bulur.

    Hedef host sabittir (api.openalex.org); kullanici girdisi yalnizca DOI'dir ve dogrulanip kacirilir, bu yuzden SSRF
    kontrolu gerekmez. Ag/API hatasinda ya da kopya yoksa None doner (log'lanir)."""

    def find_pdf_url(self, doi: str | None) -> str | None:
        normalized = normalize_doi(doi)
        if not _DOI.match(normalized):
            return None
        try:
            response = requests.get(
                _API_URL + quote(normalized, safe="/"),
                params={"select": "open_access,best_oa_location,locations"},
                headers={"User-Agent": "PKM-Kaynak-Yonetim/1.0"},
                timeout=_TIMEOUT_SECONDS,
            )
            if response.status_code != 200:
                return None
            work = response.json()
        except (requests.RequestException, ValueError) as exc:
            log.warning("Acik erisimli PDF sorgusu basarisiz: doi=%s - %s", normalized, exc)
            return None
        return self._pick_pdf_url(work)

    @staticmethod
    def _pick_pdf_url(work: dict) -> str | None:
        """En iyi acik konumun PDF'i; yoksa acik erisimli herhangi bir konumun PDF'i."""
        best = work.get("best_oa_location") or {}
        found = _http_url(best.get("pdf_url"))
        if found:
            return found
        for location in work.get("locations") or []:
            if location.get("is_oa") and _http_url(location.get("pdf_url")):
                return location["pdf_url"]
        return None
