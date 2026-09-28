from unittest.mock import MagicMock, patch
from workers.scrape_worker import ScrapeWorker
from workers.extract_worker import ExtractWorker
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
        mock_svc = MagicMock()
        mock_svc.search.return_value = {"recent": [], "popular": [], "cited": []}
        mock_svc_cls.return_value = mock_svc

        worker = MarketSearchWorker("transformer")
        received = []
        worker.signals.finished.connect(lambda results: received.append(results))
        worker.run()

        assert len(received) == 1
        assert received[0] == {"recent": [], "popular": [], "cited": []}


def test_market_search_worker_falls_back_to_empty_on_exception(qapp):
    with patch("workers.market_search_worker.PaperMarketService") as mock_svc_cls:
        mock_svc_cls.return_value.search.side_effect = RuntimeError("boom")

        worker = MarketSearchWorker("transformer")
        received = []
        worker.signals.finished.connect(lambda results: received.append(results))
        worker.run()

        assert received == [{"recent": [], "popular": [], "cited": []}]
