from unittest.mock import MagicMock, patch
from workers.scrape_worker import ScrapeWorker
from workers.extract_worker import ExtractWorker


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
