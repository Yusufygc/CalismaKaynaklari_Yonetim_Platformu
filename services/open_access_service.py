import re
from urllib.parse import quote

import requests

from core.logger import log
from utils.doi_utils import normalize_doi

_API_URL = "https://api.openalex.org/works/doi:"
_SEARCH_URL = "https://api.openalex.org/works"
_SELECT = "open_access,best_oa_location,locations"
_MIN_TITLE_KEY = 12  # bundan kisa/genel basliklar (yalnizca harf+rakam sayilir) yanlis makaleyle eslesir
_TIMEOUT_SECONDS = 10
_DOI = re.compile(r"^10\.\d{4,9}/\S+$")


def _title_key(title: object) -> str:
    """Basliklari kiyaslamak icin: kucuk harf, yalnizca harf/rakam."""
    return "".join(ch for ch in str(title or "").casefold() if ch.isalnum())


def _http_url(value: object) -> str | None:
    return value if isinstance(value, str) and value.lower().startswith(("http://", "https://")) else None


class OpenAccessService:
    """Bir makalenin (DOI'si ya da tam basligi) **acik erisimli PDF** kopyasini (yayinci sayfasi robotlara kapali olsa da arXiv,
    kurumsal arsiv, PubMed Central...) OpenAlex'ten bulur.

    Hedef host sabittir (api.openalex.org); kullanici girdisi yalnizca DOI'dir ve dogrulanip kacirilir, bu yuzden SSRF
    kontrolu gerekmez. Ag/API hatasinda ya da kopya yoksa None doner (log'lanir)."""

    def find_pdf_url(self, doi: str | None = None, title: str | None = None) -> str | None:
        """Once DOI'yle; DOI yok/sonucsuzsa basliga gore (yalnizca basligi harf/rakam bazinda AYNI olan eser kabul edilir:
        yanlis makalenin PDF'i indirilmesin)."""
        normalized = normalize_doi(doi)
        if _DOI.match(normalized):
            work = self._get_json(_API_URL + quote(normalized, safe="/"), {"select": _SELECT}, normalized)
            found = self._pick_pdf_url(work) if work else None
            if found:
                return found
        return self._find_by_title(title)

    def _find_by_title(self, title: str | None) -> str | None:
        wanted = _title_key(title)
        if len(wanted) < _MIN_TITLE_KEY:
            return None
        data = self._get_json(
            _SEARCH_URL, {"search": title, "per-page": 5, "select": "title,display_name," + _SELECT}, wanted[:40]
        )
        for work in (data or {}).get("results") or []:
            if _title_key(work.get("title") or work.get("display_name")) == wanted:
                found = self._pick_pdf_url(work)
                if found:
                    return found
        return None

    def _get_json(self, url: str, params: dict, label: str) -> dict | None:
        try:
            response = requests.get(
                url, params=params, headers={"User-Agent": "PKM-Kaynak-Yonetim/1.0"}, timeout=_TIMEOUT_SECONDS
            )
            if response.status_code != 200:
                return None
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            log.warning("Acik erisimli PDF sorgusu basarisiz: %s - %s", label, exc)
            return None

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
