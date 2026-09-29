from unittest.mock import MagicMock, patch
from workers.scrape_worker import ScrapeWorker
from workers.extract_worker import ExtractWorker
from services.paper_market_service import MarketFilters, MarketPage
from workers.market_search_worker import MarketSearchWorker


def test_scrape_worker_success(qapp):
    with patch("workers.scrape_worker.ScraperService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.extract_metadata.return_value = {"title": "Test Title"}
        mock_svc_cls.return_value = mock_svc

        worker = ScrapeWorker(1, "https://example.com")
        received = []
        worker.signals.finished.connect(lambda res_id, meta: received.append((res_id, meta)))
        worker.run()

        assert len(received) == 1
        assert received[0] == (1, {"title": "Test Title"})


def test_extract_worker_success(qapp):
    with patch("workers.extract_worker.ArticleExtractionService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.extract_full_text.return_value = "<p>Full article text</p>"
        mock_svc_cls.return_value = mock_svc

        worker = ExtractWorker(1, "https://example.com")
        received = []
        worker.signals.finished.connect(lambda res_id, text: received.append((res_id, text)))
        worker.run()

        assert len(received) == 1
        assert received[0] == (1, "<p>Full article text</p>")


def test_market_search_worker_success(qapp):
    with patch("workers.market_search_worker.PaperMarketService") as mock_svc_cls:
        pages = {"recent": MarketPage(), "popular": MarketPage(), "cited": MarketPage()}
        mock_svc_cls.return_value.search.return_value = pages

        worker = MarketSearchWorker("transformer", request_id=7)
        received = []
        worker.signals.finished.connect(lambda results, rid: received.append((results, rid)))
        worker.run()

        assert received == [(pages, 7)]


def test_market_search_worker_single_kind_requests_that_page_only(qapp):
    with patch("workers.market_search_worker.PaperMarketService") as mock_svc_cls:
        page = MarketPage(total=42)
        mock_svc_cls.return_value.search_page.return_value = page
        filters = MarketFilters(open_access=True)

        worker = MarketSearchWorker("gan", filters, kind="cited", page=3, request_id=2)
        received = []
        worker.signals.finished.connect(lambda results, rid: received.append((results, rid)))
        worker.run()

        mock_svc_cls.return_value.search_page.assert_called_once_with("gan", "cited", filters, 3)
        assert received == [({"cited": page}, 2)]


def test_market_search_worker_reports_error_pages_on_exception(qapp):
    with patch("workers.market_search_worker.PaperMarketService") as mock_svc_cls:
        mock_svc_cls.return_value.search.side_effect = RuntimeError("boom")

        worker = MarketSearchWorker("transformer")
        received = []
        worker.signals.finished.connect(lambda results, rid: received.append(results))
        worker.run()

        assert set(received[0]) == {"recent", "popular", "cited"}
        assert all(page.error == "boom" and page.items == [] for page in received[0].values())
