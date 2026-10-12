"""Vault'a not yazimi: atomik, yol guvenli, degismediyse yazmayan. Dosya sistemine yalniz bu modul dokunur."""
import codecs
import os
import time
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from core.logger import log
from pdfkit.domain.errors import VaultConflictError, VaultNoteError, VaultUnavailableError
from pdfkit.domain.vault_note import NOTE_DIRECTORY, NoteContent, compose_note, note_rel_path
from pdfkit.domain.vault_summary import SummaryContent, compose_summary

_ATTEMPTS = 3  # okuma ile degistirme arasinda dosya degisirse yeniden dene
_REPLACE_RETRIES = 4  # Windows: antivirus/arama dizinleyicisi anlik kilit tutabilir
_REPLACE_DELAY = 0.1


class WriteOutcome(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


def _snapshot(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return stat.st_mtime_ns, stat.st_size


class VaultWriter:
    """Bir vault klasorune `Papers/<citekey>.md` notlarini yazar.

    Her yazimda dosya okunur, `compose_note` ile birlestirilir; sonuc mevcut metinle ayniysa dosyaya dokunulmaz
    (Obsidian'in dosya izleyicisi gereksiz tetiklenmez). Degisiklik varsa gecici dosya + `os.replace` ile atomik
    yazilir; okuma ile degistirme arasinda dosya baska bir arac tarafindan degistiyse (kullanici Obsidian'da
    yaziyor) birlestirme yeniden yapilir, kullanicinin son hali ezilmez."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def check(self) -> None:
        """Vault klasoru kullanilabilir mi? Degilse `VaultUnavailableError`."""
        if not self._root.is_dir():
            raise VaultUnavailableError(f"Vault klasörü bulunamadı: {self._root}")
        if not os.access(self._root, os.W_OK):
            raise VaultUnavailableError(f"Vault klasörüne yazılamıyor: {self._root}")

    def write(self, content: NoteContent) -> WriteOutcome:
        self.check()
        return self._write_text(self._target(content.citekey), lambda existing: compose_note(existing, content))

    def write_summary(self, content: SummaryContent) -> WriteOutcome:
        """Kutuphane dizini / kelime defteri gibi tek dosyalik ozet notlari (sabit dosya adi). Icerik bossa ve dosya
        yoksa olusturulmaz (kelime kullanmayan kullanicinin vault'unda bos bir kelime defteri durmasin)."""
        self.check()
        target = self._summary_target(content.filename)
        if content.is_empty and not target.exists():
            return WriteOutcome.UNCHANGED
        return self._write_text(target, lambda existing: compose_summary(existing, content))

    def _write_text(self, target: Path, compose: Callable[[str | None], str]) -> WriteOutcome:
        for _ in range(_ATTEMPTS):
            before = _snapshot(target)
            existing, bom = self._read(target) if before else (None, False)
            composed = compose(existing)
            if existing is not None and composed == existing:
                return WriteOutcome.UNCHANGED
            if self._replace(target, composed, bom, before):
                return WriteOutcome.CREATED if before is None else WriteOutcome.UPDATED
        raise VaultConflictError(f"Not yazım sırasında sürekli değişti, yazılmadı: {target.name}")

    # ------------------------------------------------------------------ #

    def _target(self, citekey: str) -> Path:
        return self._notes_directory() / Path(note_rel_path(citekey)).name

    def _summary_target(self, filename: str) -> Path:
        return self._notes_directory() / filename

    def _notes_directory(self) -> Path:
        directory = self._root / NOTE_DIRECTORY
        try:
            directory.mkdir(exist_ok=True)
            resolved = directory.resolve()
            resolved.relative_to(self._root.resolve())
        except (OSError, ValueError) as exc:
            raise VaultUnavailableError(f"'{NOTE_DIRECTORY}' klasörü oluşturulamadı ya da vault dışına işaret ediyor.") from exc
        return directory

    @staticmethod
    def _read(path: Path) -> tuple[str, bool]:
        data = path.read_bytes()
        bom = data.startswith(codecs.BOM_UTF8)
        try:
            return data[len(codecs.BOM_UTF8):].decode("utf-8") if bom else data.decode("utf-8"), bom
        except UnicodeDecodeError as exc:
            raise VaultNoteError(f"Not UTF-8 değil, dokunulmadı: {path.name}") from exc

    def _replace(self, target: Path, text: str, bom: bool, before: tuple[int, int] | None) -> bool:
        """Atomik yazim. Dosya `before` aninden beri degistiyse False (cagiran yeniden birlestirir)."""
        temporary = target.with_name(f".{target.name}.pkm-tmp")
        data = (codecs.BOM_UTF8 if bom else b"") + text.encode("utf-8")
        try:
            with open(temporary, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if _snapshot(target) != before:
                return False
            for attempt in range(_REPLACE_RETRIES):
                try:
                    os.replace(temporary, target)
                    return True
                except PermissionError:
                    if attempt == _REPLACE_RETRIES - 1:
                        raise
                    time.sleep(_REPLACE_DELAY)
            return False
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                log.warning("Gecici vault dosyasi silinemedi: %s", temporary)
