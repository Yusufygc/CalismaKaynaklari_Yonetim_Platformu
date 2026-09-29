from collections import Counter
from dataclasses import dataclass

from services.paper_market_service import PaperMarketService, PaperResult

_DEFAULT_LIMIT = 20


@dataclass
class Suggestion:
    """Kutuphanedeki makalelerin ortak atif yaptigi ama kutuphanede olmayan bir eser."""

    paper: PaperResult
    cited_by_library: int  # Kutuphanede bu esere atif yapan makale sayisi


class ReadingSuggestionService:
    """"Okumadigin ortak referanslar": kutuphane makalelerinin referanslarini sayar, en cok
    atif alanlari (kutuphanede olmayanlar) onerir. Iki OpenAlex istegi yeter: kaynak
    makalelerin `referenced_works` listesi + secilen adaylarin ayrintilari."""

    def __init__(self, market: PaperMarketService | None = None) -> None:
        self._market = market or PaperMarketService()

    def suggest(
        self,
        library_openalex_ids: list[str],
        min_frequency: int | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[Suggestion]:
        """`min_frequency` verilmezse: kutuphane kucukken (<3 makale) 1, aksi halde 2 --
        yani buyuk kutuphanede yalnizca birden cok makalenin ortak atifi onerilir."""
        sources = list(dict.fromkeys(i for i in library_openalex_ids if i))
        if not sources:
            return []
        if min_frequency is None:
            min_frequency = 1 if len(sources) < 3 else 2

        references = self._market.referenced_work_ids(sources)
        owned = set(sources)
        counts: Counter[str] = Counter()
        for refs in references.values():
            counts.update(set(refs) - owned)

        # Yalnizca esik ustundekiler; ayrintilar tek istekte (en cok atif alan adaylar).
        candidates = [wid for wid, n in counts.most_common() if n >= min_frequency][: limit * 2]
        wanted = set(candidates)
        papers = self._market.works_by_ids(candidates)
        suggestions = [Suggestion(paper, counts[paper.openalex_id]) for paper in papers if paper.openalex_id in wanted]
        suggestions.sort(key=lambda s: (s.cited_by_library, s.paper.citation_count), reverse=True)
        return suggestions[:limit]
