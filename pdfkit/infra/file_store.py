import os
import re
import shutil
import time
import uuid
from pathlib import Path

from core.logger import log
from pdfkit.domain.models import StoredFile

STORE_DIR_NAME = "store"
TRASH_DIR_NAME = ".trash"
TEMP_DIR_NAME = ".tmp"
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MAX_STEM = 60


def safe_pdf_name(name: str | None) -> str:
    """Windows'ta gecerli, `.pdf` ile biten, kisa dosya adi uretir (bos ise 'belge.pdf')."""
    stem = name or ""
    if stem.lower().endswith(".pdf"):
        stem = stem[:-4]
    stem = _UNSAFE.sub("_", stem).strip(" .")[:_MAX_STEM].strip(" .")
    return f"{stem or 'belge'}.pdf"


class FileStore:
    """Icerik adresli PDF deposu: `<kok>/store/ab/<sha256>/<okunur-ad>.pdf`.

    Ayni icerik tek dosyadir (tekrar kopya olusmaz); dizin adi icerik ozeti, dosya adi ilk gorulen ad oldugu
    icin uygulama ve kullanici dosyayi okunur adla gorur. Yazma atomiktir (gecici dosya + `os.replace`); silme
    yerine `.trash/` altina tasima yapilir. Veritabani yalnizca depo koguna gore GORELI yol tutar, bu yuzden
    veri koku tasindiginda baglantilar bozulmaz.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._store = root / STORE_DIR_NAME

    @property
    def root(self) -> Path:
        return self._root

    @property
    def temp_dir(self) -> Path:
        """Indirme/kopyalama icin ayni diskte gecici alan (atomik tasima icin)."""
        path = self._store / TEMP_DIR_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _dir_rel(sha256: str) -> str:
        return f"{STORE_DIR_NAME}/{sha256[:2]}/{sha256}"

    def absolute(self, rel_path: str) -> Path:
        return self._root.joinpath(*rel_path.split("/"))

    def contains(self, path: Path) -> bool:
        """`path` bu deponun icinde mi (cozumlenmis yola gore)?"""
        return self._store.resolve() in path.resolve().parents

    def exists(self, rel_path: str) -> bool:
        return self.absolute(rel_path).is_file()

    def find(self, sha256: str) -> str | None:
        """Bu icerik depoda varsa goreli yolunu dondurur."""
        directory = self.absolute(self._dir_rel(sha256))
        if not directory.is_dir():
            return None
        for candidate in sorted(directory.glob("*.pdf")):
            return f"{self._dir_rel(sha256)}/{candidate.name}"
        return None

    def ingest(self, source: Path, sha256: str, display_name: str | None = None) -> StoredFile:
        """`source`'u depoya kopyalar (kaynak dosyaya dokunmaz). Ayni icerik varsa kopyalamaz."""
        size = source.stat().st_size
        existing = self.find(sha256)
        if existing is not None and self.absolute(existing).stat().st_size == size:
            return StoredFile(sha256, existing, size, created=False)
        rel_path = existing or f"{self._dir_rel(sha256)}/{safe_pdf_name(display_name or source.name)}"
        if existing is not None:
            log.warning("Depodaki dosya boyutu uyusmuyor, yeniden yaziliyor: %s", rel_path)
        target = self.absolute(rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(f".{uuid.uuid4().hex[:8]}.part")
        try:
            shutil.copyfile(source, partial)
            os.replace(partial, target)
        finally:
            partial.unlink(missing_ok=True)
        return StoredFile(sha256, rel_path, size, created=True)

    def quarantine(self, rel_path: str) -> bool:
        """Dosyayi `.trash/` altina tasir (kalici silme degil). Dosya yoksa True doner."""
        source = self.absolute(rel_path)
        if not source.is_file():
            return True
        trash = self._root / TRASH_DIR_NAME
        target = trash / f"{source.parent.name[:12]}_{source.name}"
        try:
            trash.mkdir(exist_ok=True)
            shutil.move(str(source), str(target))
            target.touch()
            self._remove_empty_dirs(source.parent)
        except OSError as exc:  # Windows: acik PDF kilitli olabilir
            log.warning("PDF karantinaya alinamadi: %s - %s", source, exc)
            return False
        return True

    def _remove_empty_dirs(self, directory: Path) -> None:
        for path in (directory, directory.parent):
            try:
                path.rmdir()
            except OSError:
                return

    def purge_trash(self, retention_days: int = 30) -> int:
        """Saklama suresi dolan karantina dosyalarini kalici siler; silinen sayisini dondurur."""
        trash = self._root / TRASH_DIR_NAME
        if not trash.is_dir():
            return 0
        cutoff = time.time() - retention_days * 86400
        removed = 0
        for old in trash.glob("*.pdf"):
            try:
                if old.stat().st_mtime < cutoff:
                    old.unlink()
                    removed += 1
            except OSError as exc:
                log.warning("Karantina dosyasi silinemedi: %s - %s", old, exc)
        return removed

    def stored_files(self) -> list[tuple[str, float]]:
        """Depodaki tum PDF'ler: (goreli yol, degisiklik zamani). Gecici alan haric."""
        if not self._store.is_dir():
            return []
        found = []
        for path in self._store.rglob("*.pdf"):
            if TEMP_DIR_NAME in path.relative_to(self._store).parts:
                continue
            try:
                found.append((path.relative_to(self._root).as_posix(), path.stat().st_mtime))
            except OSError:
                continue
        return found
