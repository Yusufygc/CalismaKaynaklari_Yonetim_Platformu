from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from core.logger import log
from models import Resource


def _path_from_file_url(url: str) -> Path:
    return Path(url2pathname(unquote(urlparse(url).path)))


class PdfStorageService:
    """Uygulamanin PDF depolama dizinini (kopyalanan/indirilen PDF'ler) yonetir.

    Windows'ta Qt (QML `PdfDocument`) acik PDF dosyasini, okuyucu kapansa bile
    surec sonlanana kadar kilitli tutabiliyor -- bu yuzden kaynak silinirken
    dosya her zaman hemen silinemiyor. Hicbir kaynaga bagli olmayan (yetim)
    dosyalar uygulama acilisinda buradan temizlenir.
    """

    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir

    @staticmethod
    def referenced_paths(resources: list[Resource]) -> set[Path]:
        paths: set[Path] = set()
        for resource in resources:
            if resource.url and resource.url.startswith("file://") and resource.url.lower().endswith(".pdf"):
                paths.add(_path_from_file_url(resource.url).resolve())
            local = (resource.extra_metadata or {}).get("local_pdf")
            if local:
                paths.add(Path(local).resolve())
        return paths

    def sweep_orphans(self, resources: list[Resource]) -> int:
        """Hicbir kaynaga bagli olmayan *.pdf dosyalarini siler; silinen sayisini dondurur."""
        if not self._storage_dir.is_dir():
            return 0
        referenced = self.referenced_paths(resources)
        removed = 0
        for pdf in self._storage_dir.glob("*.pdf"):
            if pdf.resolve() in referenced:
                continue
            try:
                pdf.unlink()
                removed += 1
            except OSError as exc:
                log.warning("Yetim PDF silinemedi: %s - %s", pdf, exc)
        if removed:
            log.info("Yetim PDF temizligi: %d dosya silindi.", removed)
        return removed
