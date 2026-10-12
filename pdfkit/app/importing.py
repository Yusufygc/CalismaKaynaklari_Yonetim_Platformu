from pathlib import Path

from pdfkit.domain.models import PreparedPdf
from pdfkit.infra.downloader import Fetch, download_to_temp
from pdfkit.infra.file_store import FileStore
from pdfkit.infra.hashing import sha256_file
from pdfkit.infra.inspector import inspect_pdf


def prepare_pdf(source: Path, store: FileStore, original_filename: str | None = None) -> PreparedPdf:
    """Disaridaki bir PDF'i inceler, SHA-256'sini hesaplar ve depoya alir (kaynak dosyaya dokunmaz).

    Veritabanina DOKUNMAZ: arka plan thread'inde guvenle calisir; sonucu ana thread'de
    `DocumentService.register` kaydeder. Gecersiz/sifreli PDF'te `NotAPdfError`, kopyalama hatasinda `OSError`."""
    inspection = inspect_pdf(source)  # Bozuk dosyayi kopyalamadan once reddet.
    name = original_filename or source.name
    stored = store.ingest(source, sha256_file(source), display_name=name)
    return PreparedPdf(stored=stored, inspection=inspection, original_filename=name)


def prepare_remote_pdf(url: str, store: FileStore, *, fetch: Fetch, max_bytes: int) -> PreparedPdf:
    """Uzak PDF'i akis halinde indirir ve `prepare_pdf` ile depoya alir. Gecici dosya her durumda silinir."""
    temp = download_to_temp(url, fetch=fetch, temp_dir=store.temp_dir, max_bytes=max_bytes)
    try:
        return prepare_pdf(temp, store, original_filename=_filename_from_url(url))
    finally:
        temp.unlink(missing_ok=True)


def _filename_from_url(url: str) -> str | None:
    from urllib.parse import unquote, urlparse

    name = Path(unquote(urlparse(url).path)).name
    return name or None
