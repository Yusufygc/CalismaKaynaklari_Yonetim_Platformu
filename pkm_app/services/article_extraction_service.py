import trafilatura

from core.logger import log
from core.net_utils import is_blocked_host


class ArticleExtractionService:
    """Web makalelerinin govde metnini cikarir (okuyucu sayfasi icin).

    ScraperService'ten ayri tutulur: ScraperService hafif og:meta scraping
    yapar, burada trafilatura tum sayfayi indirip boilerplate-temizleme
    sezgiseli calistirir -- farkli sorumluluk, farkli hata modu (None doner).
    """

    def extract_full_text(self, url: str) -> str | None:
        if is_blocked_host(url):
            log.warning("URL ic ag/loopback adresine cozumlendigi icin reddedildi: %s", url)
            return None
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None
            return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        except Exception as exc:
            log.warning("Tam metin cikarilamadi: %s - %s", url, exc)
            return None
