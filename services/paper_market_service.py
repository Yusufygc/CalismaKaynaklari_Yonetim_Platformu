from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import requests

from core.logger import log

_TIMEOUT_SECONDS = 10
_PER_PAGE = 10
_MAX_BATCH = 50  # openalex:W1|W2|... filtresinde tek istekte sorgulanan en fazla kimlik
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
    doi: str | None = None
    openalex_id: str | None = None
    venue: str | None = None
    is_open_access: bool = False
    has_pdf: bool = False
    # `authors` ile ayni sirada OpenAlex yazar kimlikleri (bilinmiyorsa '').
    author_ids: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict:
        """Kaynagin `extra_metadata`'sina yazilacak akademik bilgiler (atif uretimi icin)."""
        metadata = {
            "authors": self.authors,
            "year": self.year,
            "citation_count": self.citation_count,
            "venue": self.venue,
            "doi": self.doi,
            "openalex_id": self.openalex_id,
            "source": "openalex",
        }
        return {k: v for k, v in metadata.items() if v not in (None, "", [])}


# Sekme -> OpenAlex sort (None: alaka duzeyi).
MARKET_SORTS: dict[str, str | None] = {
    "recent": "publication_date:desc",
    "popular": None,
    "cited": "cited_by_count:desc",
}

_AUTHOR_ID = re.compile(r"A\d+")
_WORK_ID = re.compile(r"W\d+")
_DOI = re.compile(r"10\.\d{4,9}/\S+")
_WORK_TYPES = {"article", "review", "preprint", "book", "dissertation"}


def _parse_year(raw) -> int | None:
    try:
        value = int(raw or 0)
    except (TypeError, ValueError):
        return None
    return value if 1000 <= value <= 3000 else None


def _parse_author_id(raw) -> str:
    author_id = str(raw or "").strip().upper()
    return author_id if _AUTHOR_ID.fullmatch(author_id) else ""


def _parse_work_type(raw) -> str:
    work_type = str(raw or "").strip().lower()
    return work_type if work_type in _WORK_TYPES else ""


def _parse_language(raw) -> str:
    language = str(raw or "").strip().lower()
    return language if language.isalpha() and len(language) == 2 else ""


@dataclass(frozen=True)
class MarketFilters:
    """Makale Market arama filtreleri; OpenAlex `filter=` ifadesine cevrilir."""

    year_from: int | None = None
    year_to: int | None = None
    open_access: bool = False
    work_type: str = ""
    language: str = ""
    author_id: str = ""

    @classmethod
    def from_dict(cls, data: dict | None) -> MarketFilters:
        """QML'den gelen gevsek dict'i (bos/gecersiz alanlar yok sayilir) filtreye cevirir."""
        data = data or {}
        return cls(
            author_id=_parse_author_id(data.get("authorId")),
            year_from=_parse_year(data.get("yearFrom")),
            year_to=_parse_year(data.get("yearTo")),
            open_access=bool(data.get("openAccess")),
            work_type=_parse_work_type(data.get("workType")),
            language=_parse_language(data.get("language")),
        )

    def to_openalex(self) -> str:
        parts = []
        if self.year_from:
            parts.append(f"from_publication_date:{self.year_from}-01-01")
        if self.year_to:
            parts.append(f"to_publication_date:{self.year_to}-12-31")
        if self.open_access:
            parts.append("is_oa:true")
        if self.work_type:
            parts.append(f"type:{self.work_type}")
        if self.language:
            parts.append(f"language:{self.language}")
        if self.author_id:
            parts.append(f"author.id:{self.author_id}")
        return ",".join(parts)


@dataclass
class MarketPage:
    """Bir sekmenin bir sayfasi: sonuclar, toplam kayit sayisi ve (varsa) hata."""

    items: list[PaperResult] = field(default_factory=list)
    total: int = 0
    error: str = ""


def _valid_work_ids(openalex_ids: list[str]) -> list[str]:
    """Toplu `openalex:W1|W2` filtresine girecek gecerli kimlikler (en fazla `_MAX_BATCH`); gecersizler elenir."""
    return [i for i in openalex_ids if _WORK_ID.fullmatch(i or "")][:_MAX_BATCH]


def _short_openalex_id(work_id: str | None) -> str | None:
    """'https://openalex.org/W2741809807' -> 'W2741809807'."""
    if not work_id:
        return None
    return work_id.rstrip("/").rsplit("/", 1)[-1]


def _clean_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    return doi.replace("https://doi.org/", "").replace("http://doi.org/", "")


def _title_key(title: str | None) -> str:
    """Basliklari kiyaslamak icin: kucuk harf, yalnizca harf/rakam."""
    return "".join(ch for ch in (title or "").casefold() if ch.isalnum())


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


def _authors_and_ids(work: dict) -> tuple[list[str], list[str]]:
    """Adi olan yazarlar ve ayni siradaki OpenAlex kimlikleri (bilinmiyorsa '')."""
    named = [a["author"] for a in work.get("authorships", []) if (a.get("author") or {}).get("display_name")]
    return [a["display_name"] for a in named], [_short_openalex_id(a.get("id")) or "" for a in named]


def _to_paper_result(work: dict) -> PaperResult | None:
    url = _best_url(work)
    if not url:
        return None
    authors, author_ids = _authors_and_ids(work)
    location = work.get("primary_location") or {}
    return PaperResult(
        title=work.get("title") or work.get("display_name") or "(Baslik yok)",
        authors=authors,
        year=work.get("publication_year"),
        citation_count=work.get("cited_by_count") or 0,
        url=url,
        abstract=_reconstruct_abstract(work.get("abstract_inverted_index")),
        doi=_clean_doi(work.get("doi")),
        openalex_id=_short_openalex_id(work.get("id")),
        venue=(location.get("source") or {}).get("display_name"),
        is_open_access=bool((work.get("open_access") or {}).get("is_oa")),
        has_pdf=bool(location.get("pdf_url")),
        author_ids=author_ids,
    )


def _search_params(topic: str, kind: str, filters: MarketFilters | None, page: int) -> dict:
    """Sekme icin OpenAlex sorgu parametreleri; gecersiz sekmede ValueError."""
    if kind not in MARKET_SORTS:
        raise ValueError(f"Gecersiz sekme: {kind}")
    params: dict = {"per-page": _PER_PAGE, "page": max(1, page)}
    if topic:  # Yazar aramasinda konu bos olabilir (yalnizca `author.id` filtresi).
        params["search"] = topic
    sort = MARKET_SORTS[kind]
    if sort:
        params["sort"] = sort
    filter_expr = (filters or MarketFilters()).to_openalex()
    if filter_expr:
        params["filter"] = filter_expr
    return params


class PaperMarketService:
    """OpenAlex Works API uzerinden konu bazli akademik makale aramasi.

    Sabit/guvenilir bir host'a (api.openalex.org) sorgu atildigi icin
    is_blocked_host SSRF kontrolu gerekmiyor -- kullanici girdisi bir
    URL degil arama metni, hedef host hardcoded.
    """

    def search(self, topic: str, filters: MarketFilters | None = None) -> dict[str, MarketPage]:
        """Uc sekme (guncel/populer/atif) icin ilk sayfayi getirir."""
        return {kind: self.search_page(topic, kind, filters) for kind in MARKET_SORTS}

    def search_page(
        self, topic: str, kind: str, filters: MarketFilters | None = None, page: int = 1
    ) -> MarketPage:
        """Tek bir sekmenin `page`. sayfasi. Hata `MarketPage.error`'a yazilir
        (arayuz 'sonuc yok' ile 'ulasilamadi' ayrimini yapabilsin diye)."""
        params = _search_params(topic, kind, filters, page)
        try:
            works, total = self._get_page(params)
        except Exception as exc:
            log.warning("Makale market sorgusu basarisiz: konu=%s sekme=%s - %s", topic, kind, exc)
            return MarketPage(error=str(exc) or exc.__class__.__name__)

        items = [p for p in (_to_paper_result(w) for w in works) if p is not None]
        return MarketPage(items=items, total=total)

    def find_paper(self, doi: str | None = None, title: str | None = None) -> PaperResult | None:
        """Bir makalenin OpenAlex kaydini DOI'yle (kesin) ya da basliga gore (en iyi eslesme) getirir.

        Ag/API hatasinda None doner (log'lanir) -- 'bulunamadi' ile 'ulasilamadi'
        ayrimi icin `find_paper_strict` kullan.
        """
        try:
            return self.find_paper_strict(doi=doi, title=title)
        except Exception as exc:
            log.warning("Makale bilgisi getirilemedi: doi=%s title=%s - %s", doi, title, exc)
            return None

    def find_paper_strict(self, doi: str | None = None, title: str | None = None) -> PaperResult | None:
        """`find_paper` ile ayni ama ag/API hatalarini firlatir; bulunamazsa None doner."""
        clean_doi = _clean_doi(doi)
        if clean_doi and _DOI.fullmatch(clean_doi):  # Bicimsiz DOI URL yoluna girmez; basliga dusulur.
            work = self._get_json(f"{_API_URL}/https://doi.org/{clean_doi}", {})
            if work:
                return _to_paper_result(work)
            # OpenAlex bazi DOI'leri (arXiv 10.48550/arXiv.*, yeni DOI'ler) `works/<doi>` ile bulamaz:
            # baslik varsa baslik aramasina dusulur, ama yanlis makale donmesin diye baslik esitligi sarttir.
            return self._find_by_title(title, exact=True)
        return self._find_by_title(title)

    def _find_by_title(self, title: str | None, exact: bool = False) -> PaperResult | None:
        """Baslik aramasinin ilk sonucu; `exact` ise yalniz basligi (harf/rakam bazinda) ayni olan sonuc."""
        if not title:
            return None
        works = self._get_results({"search": title, "per-page": 5 if exact else 1})
        if exact:
            wanted = _title_key(title)
            works = [w for w in works if _title_key(w.get("title") or w.get("display_name")) == wanted]
        return _to_paper_result(works[0]) if works else None

    def related_papers(self, openalex_id: str, kind: str, limit: int = 25) -> list[PaperResult]:
        """`kind='references'`: bu makalenin atif yaptigi eserler; `kind='citations'`: ona atif yapanlar;
        `kind='similar'`: OpenAlex'in benzer buldugu eserler; `kind='author'` (`openalex_id` = yazar
        kimligi): yazarin eserleri.

        Sonuclar atif sayisina gore azalan sirali. Ag hatasinda istisna firlatir
        (arayuz 'yuklenemedi' ile 'kayit yok' ayrimini yapabilsin diye).
        """
        filters = {
            "references": f"cited_by:{openalex_id}",
            "citations": f"cites:{openalex_id}",
            "similar": f"related_to:{openalex_id}",
            "author": f"author.id:{openalex_id}",
        }
        if kind not in filters:
            raise ValueError(f"Gecersiz iliski turu: {kind}")
        # Kimlik `filter=` ifadesine girdigi icin dogrulanir (`W1,type:x` gibi ek filtre enjekte edilemez).
        expected = _AUTHOR_ID if kind == "author" else _WORK_ID
        if not expected.fullmatch(openalex_id or ""):
            raise ValueError(f"Gecersiz OpenAlex kimligi: {openalex_id!r}")
        works = self._get_results(
            {"filter": filters[kind], "sort": "cited_by_count:desc", "per-page": limit}
        )
        return [p for p in (_to_paper_result(w) for w in works) if p is not None]

    def referenced_work_ids(self, openalex_ids: list[str]) -> dict[str, list[str]]:
        """Her makale icin atif yaptigi eserlerin (kisa) OpenAlex kimlikleri. Tek istekte en fazla
        `_MAX_BATCH` makale sorgulanir."""
        result: dict[str, list[str]] = {}
        ids = _valid_work_ids(openalex_ids)
        if not ids:
            return result
        works = self._get_results(
            {"filter": f"openalex:{'|'.join(ids)}", "select": "id,referenced_works", "per-page": _MAX_BATCH}
        )
        for work in works:
            work_id = _short_openalex_id(work.get("id"))
            if work_id:
                result[work_id] = [
                    r for r in (_short_openalex_id(ref) for ref in work.get("referenced_works") or []) if r
                ]
        return result

    def works_by_ids(self, openalex_ids: list[str]) -> list[PaperResult]:
        """Verilen (kisa) OpenAlex kimliklerine ait eserler (en fazla `_MAX_BATCH`)."""
        ids = _valid_work_ids(openalex_ids)
        if not ids:
            return []
        works = self._get_results({"filter": f"openalex:{'|'.join(ids)}", "per-page": _MAX_BATCH})
        return [p for p in (_to_paper_result(w) for w in works) if p is not None]

    def _get_json(self, url: str, params: dict) -> dict | None:
        response = requests.get(url, params=params, headers=_HEADERS, timeout=_TIMEOUT_SECONDS)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def _get_results(self, params: dict) -> list[dict]:
        return self._get_page(params)[0]

    def _get_page(self, params: dict) -> tuple[list[dict], int]:
        """(sonuclar, toplam kayit sayisi). Anonim havuzda goruldugu uzere (429)
        bir kez kisa bekleyip yeniden dener."""
        for attempt in range(2):
            response = requests.get(_API_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT_SECONDS)
            if response.status_code in (429, 502, 503, 504) and attempt == 0:
                time.sleep(1)
                continue
            response.raise_for_status()
            body = response.json()
            results = body.get("results", [])
            return results, (body.get("meta") or {}).get("count", len(results))
        return [], 0
