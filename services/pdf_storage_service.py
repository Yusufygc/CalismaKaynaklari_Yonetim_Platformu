import shutil
import time
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from core.logger import log
from models import Resource


TRASH_DIR_NAME = ".trash"
TRASH_RETENTION_DAYS = 30


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
        """Hicbir kaynaga bagli olmayan *.pdf dosyalarini `.trash/` altina tasir (silmez); tasinan sayiyi dondurur.

        Koruma: kaynak listesi bossa (yeni/yanlis/sifirlanmis veritabani, eski yedek geri yuklemesi) hicbir
        dosyaya dokunulmaz -- aksi halde tum PDF'ler yetim sayilirdi. Karantinadaki dosyalar
        `TRASH_RETENTION_DAYS` gun sonra kalici silinir."""
        if not self._storage_dir.is_dir():
            return 0
        self._purge_trash()
        if not resources:
            return 0
        referenced = self.referenced_paths(resources)
        moved = 0
        for pdf in self._storage_dir.glob("*.pdf"):
            if pdf.resolve() in referenced:
                continue
            if self._quarantine(pdf):
                moved += 1
        if moved:
            log.info("Yetim PDF temizligi: %d dosya karantinaya alindi (%s).", moved, TRASH_DIR_NAME)
        return moved

    def _quarantine(self, pdf: Path) -> bool:
        trash = self._storage_dir / TRASH_DIR_NAME
        try:
            trash.mkdir(exist_ok=True)
            shutil.move(str(pdf), str(trash / pdf.name))
            (trash / pdf.name).touch()  # Saklama suresi tasima aninda baslar.
        except OSError as exc:
            log.warning("Yetim PDF karantinaya alinamadi: %s - %s", pdf, exc)
            return False
        return True

    def _purge_trash(self) -> None:
        trash = self._storage_dir / TRASH_DIR_NAME
        if not trash.is_dir():
            return
        cutoff = time.time() - TRASH_RETENTION_DAYS * 86400
        for old in trash.glob("*.pdf"):
            try:
                if old.stat().st_mtime < cutoff:
                    old.unlink()
            except OSError as exc:
                log.warning("Karantina dosyasi silinemedi: %s - %s", old, exc)
