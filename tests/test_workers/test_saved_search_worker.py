from unittest.mock import patch

from services.paper_market_service import MarketPage, PaperResult
from workers.saved_search_worker import SavedSearchCheckWorker


def _paper(openalex_id: str) -> PaperResult:
    return PaperResult(
        title=openalex_id, authors=[], year=2024, citation_count=0, url="https://x.org",
        abstract=None, openalex_id=openalex_id,
    )


def test_saved_search_check_worker_counts_unseen_and_reports_errors(qapp):
    pages = {
        "gan": MarketPage(items=[_paper("W1"), _paper("W2"), _paper("W3")], total=3),
        "err": MarketPage(error="offline"),
    }
    with patch("workers.saved_search_worker.PaperMarketService") as svc_cls:
        svc_cls.return_value.search_page.side_effect = lambda topic, kind, filters: pages[topic]
        worker = SavedSearchCheckWorker(
            [
                {"id": 1, "topic": "gan", "filters": {"yearFrom": "2020"}, "seenIds": ["W2"]},
                {"id": 2, "topic": "err", "filters": {}, "seenIds": []},
            ]
        )
        received = []
        worker.signals.finished.connect(received.append)
        worker.run()

    assert received == [
        [
            {"id": 1, "newCount": 2, "error": ""},
            {"id": 2, "newCount": 0, "error": "offline"},
        ]
    ]
    first_call = svc_cls.return_value.search_page.call_args_list[0]
    assert first_call.args[1] == "recent"
    assert first_call.args[2].year_from == 2020
