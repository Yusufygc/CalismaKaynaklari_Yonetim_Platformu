from unittest.mock import MagicMock

from services.paper_market_service import PaperResult
from services.reading_suggestion_service import ReadingSuggestionService


def _paper(openalex_id: str, citations: int = 0) -> PaperResult:
    return PaperResult(
        title=f"Paper {openalex_id}", authors=[], year=2020, citation_count=citations,
        url=f"https://x.org/{openalex_id}", abstract=None, openalex_id=openalex_id,
    )


def _service(references: dict, papers: list[PaperResult]) -> tuple[ReadingSuggestionService, MagicMock]:
    market = MagicMock()
    market.referenced_work_ids.return_value = references
    market.works_by_ids.return_value = papers
    return ReadingSuggestionService(market), market


def test_no_library_ids_returns_nothing_without_network():
    service, market = _service({}, [])

    assert service.suggest([]) == []
    market.referenced_work_ids.assert_not_called()


def test_ranks_by_library_frequency_then_citations():
    refs = {
        "W1": ["W10", "W11", "W12"],
        "W2": ["W10", "W11"],
        "W3": ["W10", "W13"],
    }
    papers = [_paper("W10", 5), _paper("W11", 900), _paper("W12", 1), _paper("W13", 1)]
    service, market = _service(refs, papers)

    result = service.suggest(["W1", "W2", "W3"])

    # 3 makale -> esik 2: yalnizca W10 (3x) ve W11 (2x).
    market.works_by_ids.assert_called_once()
    assert set(market.works_by_ids.call_args.args[0]) == {"W10", "W11"}
    assert [(s.paper.openalex_id, s.cited_by_library) for s in result] == [("W10", 3), ("W11", 2)]


def test_small_library_uses_frequency_one():
    service, market = _service({"W1": ["W10", "W11"]}, [_paper("W10"), _paper("W11")])

    result = service.suggest(["W1"])

    assert {s.paper.openalex_id for s in result} == {"W10", "W11"}


def test_excludes_works_already_in_library():
    service, market = _service({"W1": ["W2", "W10"], "W2": ["W1", "W10"]}, [_paper("W10")])

    service.suggest(["W1", "W2"])

    assert market.works_by_ids.call_args.args[0] == ["W10"]


def test_drops_candidates_the_lookup_did_not_return():
    service, _ = _service({"W1": ["W10", "W11"]}, [_paper("W10")])

    assert [s.paper.openalex_id for s in service.suggest(["W1"])] == ["W10"]


def test_respects_limit_and_duplicates_in_input():
    refs = {"W1": [f"W{n}" for n in range(100, 130)]}
    service, _ = _service(refs, [_paper(f"W{n}", n) for n in range(100, 130)])

    assert len(service.suggest(["W1", "W1"], limit=5)) == 5
