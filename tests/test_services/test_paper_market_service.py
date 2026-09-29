from unittest.mock import MagicMock, patch

import pytest

from services.paper_market_service import (
    MarketFilters,
    PaperMarketService,
)


def _work(n: int) -> dict:
    return {
        "id": f"https://openalex.org/W{n}",
        "title": f"Paper {n}",
        "publication_year": 2020,
        "cited_by_count": n,
        "doi": f"https://doi.org/10.1/{n}",
        "primary_location": {"landing_page_url": f"https://example.org/{n}"},
    }


def _response(works: list[dict], count: int | None = None, status: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.json.return_value = {"results": works, "meta": {"count": len(works) if count is None else count}}
    return response


class TestMarketFilters:
    def test_empty_filters_produce_no_expression(self):
        assert MarketFilters().to_openalex() == ""
        assert MarketFilters().is_empty()

    def test_all_filters_are_combined(self):
        expr = MarketFilters(
            year_from=2020, year_to=2024, open_access=True, work_type="review", language="tr"
        ).to_openalex()

        assert expr == (
            "from_publication_date:2020-01-01,to_publication_date:2024-12-31,"
            "is_oa:true,type:review,language:tr"
        )

    def test_from_dict_ignores_invalid_values(self):
        filters = MarketFilters.from_dict(
            {"yearFrom": "abc", "yearTo": "99999", "workType": "; drop", "language": "turkish"}
        )

        assert filters.is_empty()

    def test_from_dict_parses_qml_map(self):
        filters = MarketFilters.from_dict(
            {"yearFrom": "2019", "yearTo": "", "openAccess": True, "workType": "Article", "language": "EN"}
        )

        assert filters == MarketFilters(year_from=2019, open_access=True, work_type="article", language="en")

    def test_from_dict_accepts_none(self):
        assert MarketFilters.from_dict(None).is_empty()


class TestSearchPage:
    def test_sends_filter_sort_and_page_params(self):
        with patch("services.paper_market_service.requests.get", return_value=_response([_work(1)], count=57)) as get:
            page = PaperMarketService().search_page(
                "gan", "cited", MarketFilters(open_access=True), page=3
            )

        params = get.call_args.kwargs["params"]
        assert params["search"] == "gan"
        assert params["sort"] == "cited_by_count:desc"
        assert params["filter"] == "is_oa:true"
        assert params["page"] == 3
        assert page.total == 57
        assert [p.title for p in page.items] == ["Paper 1"]
        assert page.error == ""

    def test_relevance_tab_has_no_sort_and_no_filter_when_unfiltered(self):
        with patch("services.paper_market_service.requests.get", return_value=_response([])) as get:
            PaperMarketService().search_page("gan", "popular")

        params = get.call_args.kwargs["params"]
        assert "sort" not in params and "filter" not in params

    def test_network_error_is_reported_not_swallowed_as_empty(self):
        with patch("services.paper_market_service.requests.get", side_effect=ConnectionError("offline")):
            page = PaperMarketService().search_page("gan", "recent")

        assert page.items == [] and page.total == 0
        assert page.error == "offline"

    def test_retries_once_on_rate_limit(self):
        responses = [_response([], status=429), _response([_work(2)])]
        with patch("services.paper_market_service.requests.get", side_effect=responses), \
                patch("services.paper_market_service.time.sleep"):
            page = PaperMarketService().search_page("gan", "recent")

        assert [p.title for p in page.items] == ["Paper 2"]

    def test_invalid_kind_raises(self):
        with pytest.raises(ValueError):
            PaperMarketService().search_page("gan", "bogus")

    def test_search_returns_three_tabs(self):
        with patch("services.paper_market_service.requests.get", return_value=_response([_work(1)])):
            pages = PaperMarketService().search("gan")

        assert set(pages) == {"recent", "popular", "cited"}
        assert all(len(p.items) == 1 for p in pages.values())


class TestPaperResultFlags:
    def test_open_access_and_pdf_flags(self):
        from services.paper_market_service import _to_paper_result

        work = _work(1)
        work["open_access"] = {"is_oa": True}
        work["primary_location"]["pdf_url"] = "https://example.org/1.pdf"

        paper = _to_paper_result(work)

        assert paper.is_open_access is True and paper.has_pdf is True

    def test_flags_default_to_false(self):
        from services.paper_market_service import _to_paper_result

        paper = _to_paper_result(_work(1))

        assert paper.is_open_access is False and paper.has_pdf is False


class TestDiscovery:
    def test_related_kinds_map_to_openalex_filters(self):
        expected = {
            "references": "cited_by:W1",
            "citations": "cites:W1",
            "similar": "related_to:W1",
            "author": "author.id:W1",
        }
        for kind, filter_expr in expected.items():
            with patch("services.paper_market_service.requests.get", return_value=_response([_work(1)])) as get:
                papers = PaperMarketService().related_papers("W1", kind)

            assert get.call_args.kwargs["params"]["filter"] == filter_expr
            assert len(papers) == 1

    def test_invalid_related_kind_raises(self):
        with pytest.raises(ValueError):
            PaperMarketService().related_papers("W1", "bogus")

    def test_author_ids_align_with_named_authors(self):
        from services.paper_market_service import _to_paper_result

        work = _work(1)
        work["authorships"] = [
            {"author": {"id": "https://openalex.org/A11", "display_name": "Ada"}},
            {"author": {"id": "https://openalex.org/A12"}},  # adsiz: atlanir
            {"author": {"display_name": "Grace"}},  # kimliksiz
        ]

        paper = _to_paper_result(work)

        assert paper.authors == ["Ada", "Grace"]
        assert paper.author_ids == ["A11", ""]

    def test_author_filter_only_search_has_no_search_param(self):
        with patch("services.paper_market_service.requests.get", return_value=_response([_work(1)])) as get:
            PaperMarketService().search_page("", "cited", MarketFilters(author_id="A123"))

        params = get.call_args.kwargs["params"]
        assert "search" not in params
        assert params["filter"] == "author.id:A123"

    def test_author_id_is_validated(self):
        assert MarketFilters.from_dict({"authorId": "a5103024730"}).author_id == "A5103024730"
        assert MarketFilters.from_dict({"authorId": "A1,type:x"}).author_id == ""

    def test_referenced_work_ids_returns_short_ids(self):
        body = [
            {"id": "https://openalex.org/W1", "referenced_works": ["https://openalex.org/W7", "https://openalex.org/W8"]},
            {"id": "https://openalex.org/W2", "referenced_works": None},
        ]
        with patch("services.paper_market_service.requests.get", return_value=_response(body)) as get:
            result = PaperMarketService().referenced_work_ids(["W1", "W2"])

        assert get.call_args.kwargs["params"]["filter"] == "openalex:W1|W2"
        assert result == {"W1": ["W7", "W8"], "W2": []}

    def test_works_by_ids_empty_makes_no_request(self):
        with patch("services.paper_market_service.requests.get") as get:
            assert PaperMarketService().works_by_ids([]) == []
            assert PaperMarketService().referenced_work_ids([]) == {}

        get.assert_not_called()
