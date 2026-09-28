import time
from dataclasses import dataclass

import requests

from core.logger import log

_TIMEOUT_SECONDS = 10
_PER_PAGE = 10
_API_URL = "https://api.openalex.org/works"
_HEADERS = {"User-Agent": "KaynakYonetimPlatformu/1.0"}


@dataclass
class PaperResult:
    title: str
    authors: list[str]
    year: int | None
    citation_count: int
    url: str | None
    abstract: str | None


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """OpenAlex ozeti kelime->pozisyon ters-indeksi olarak doner; duz metne cevirir."""
    if not inverted_index:
        return None
    max_pos = max(p for positions in inverted_index.values() for p in positions)
    words = [""] * (max_pos + 1)
    for word, positions in inverted_index.items():
        for p in positions:
            words[p] = word
    return " ".join(words).strip() or None


def _best_url(work: dict) -> str | None:
    location = work.get("primary_location") or {}
    if location.get("pdf_url"):
        return location["pdf_url"]
    if location.get("landing_page_url"):
        return location["landing_page_url"]
    if work.get("doi"):
        return work["doi"] if work["doi"].startswith("http") else f"https://doi.org/{work['doi']}"
    return None


def _to_paper_result(work: dict) -> PaperResult | None:
    url = _best_url(work)
    if not url:
        return None
    authors = [
        a["author"]["display_name"]
        for a in work.get("authorships", [])
        if a.get("author") and a["author"].get("display_name")
    ]
    return PaperResult(
        title=work.get("title") or work.get("display_name") or "(Baslik yok)",
        authors=authors,
        year=work.get("publication_year"),
        citation_count=work.get("cited_by_count") or 0,
        url=url,
        abstract=_reconstruct_abstract(work.get("abstract_inverted_index")),
    )


class PaperMarketService:
    """OpenAlex Works API uzerinden konu bazli akademik makale aramasi.

    Sabit/guvenilir bir host'a (api.openalex.org) sorgu atildigi icin
    is_blocked_host SSRF kontrolu gerekmiyor -- kullanici girdisi bir
    URL degil arama metni, hedef host hardcoded.
    """

    def search(self, topic: str) -> dict[str, list[PaperResult]]:
        return {
            "recent": self._query(topic, sort="publication_date:desc"),
            "popular": self._query(topic, sort=None),
            "cited": self._query(topic, sort="cited_by_count:desc"),
        }

    def _query(self, topic: str, sort: str | None) -> list[PaperResult]:
        params = {"search": topic, "per-page": _PER_PAGE}
        if sort:
            params["sort"] = sort
        try:
            works = self._get_results(params)
        except Exception as exc:
            log.warning("Makale market sorgusu basarisiz: konu=%s sort=%s - %s", topic, sort, exc)
            return []

        results = []
        for work in works:
            paper = _to_paper_result(work)
            if paper is not None:
                results.append(paper)
        return results

    def _get_results(self, params: dict) -> list[dict]:
        """Anonim havuzda goruldugu uzere (429) bir kez kisa bekleyip yeniden dener."""
        for attempt in range(2):
            response = requests.get(_API_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT_SECONDS)
            if response.status_code == 429 and attempt == 0:
                time.sleep(1)
                continue
            response.raise_for_status()
            return response.json().get("results", [])
        return []
