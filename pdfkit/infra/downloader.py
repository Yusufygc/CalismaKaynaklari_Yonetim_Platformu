import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.logger import log
from pdfkit.domain.errors import DownloadError, TooLargeError

PDF_MAGIC = b"%PDF-"
_CHUNK = 64 * 1024

# fetch(url) -> akis halinde (stream=True) yanit nesnesi ya da None (reddedildi: ic ag / yonlendirme siniri).
# Yanit: `.iter_content(chunk_size)`, `.headers`, `.close()`. SSRF korumasi saglayici tarafindadir (app katmani).
Fetch = Callable[[str], Any]


def download_to_temp(
    url: str, *, fetch: Fetch, temp_dir: Path, max_bytes: int, deadline_seconds: float = 180.0
) -> Path:
    """PDF'i akis halinde gecici dosyaya indirir. Boyut siniri indirirken denetlenir (govdenin tamami
    belleğe alinmaz); ilk bayt `%PDF-` degilse ya da sure/boyut asilirsa gecici dosya silinip hata firlatilir."""
    response = fetch(url)
    if response is None:
        raise DownloadError(f"Indirme reddedildi (ic ag ya da yonlendirme siniri): {url}")
    try:
        declared = _declared_length(response)
        if declared is not None and declared > max_bytes:
            raise TooLargeError(f"PDF cok buyuk ({declared} bayt): {url}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        target = temp_dir / f"{uuid.uuid4().hex}.part"
        try:
            _write_stream(response, target, max_bytes, time.monotonic() + deadline_seconds, url)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return target
    finally:
        close = getattr(response, "close", None)
        if close:
            close()


def _declared_length(response: Any) -> int | None:
    raw = getattr(response, "headers", {}).get("Content-Length")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _write_stream(response: Any, target: Path, max_bytes: int, deadline: float, url: str) -> None:
    written = 0
    with target.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=_CHUNK):
            if not chunk:
                continue
            if written == 0 and not chunk.startswith(PDF_MAGIC):
                log.info("URL bir PDF degil (imza uyusmuyor): %s", url)
                raise DownloadError(f"URL bir PDF degil: {url}")
            written += len(chunk)
            if written > max_bytes:
                raise TooLargeError(f"PDF cok buyuk (>{max_bytes} bayt): {url}")
            if time.monotonic() > deadline:
                raise DownloadError(f"Indirme zaman asimina ugradi: {url}")
            handle.write(chunk)
    if written == 0:
        raise DownloadError(f"Bos yanit: {url}")
