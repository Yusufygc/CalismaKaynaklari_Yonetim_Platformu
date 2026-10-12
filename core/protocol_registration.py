"""Windows'ta `pkm://` URL protokolunu bu uygulamaya baglar (kullanici bazli: HKCU, yonetici yetkisi gerekmez).

Kayit istege baglidir ve yalnizca kullanicinin Ayarlar'daki dugmesiyle yapilir. Obsidian notlarindaki
`pkm://open?...` baglantilari tiklaninca isletim sistemi `uygulama "<baglanti>"` komutunu calistirir."""
import sys
from pathlib import Path
from types import ModuleType

SCHEME = "pkm"
_KEY = rf"Software\Classes\{SCHEME}"


def expected_command(frozen: bool | None = None, executable: str | None = None, entry_script: Path | None = None) -> str:
    """Kayda yazilacak komut: paketli uygulamada `"app.exe" "%1"`, gelistirmede `"python.exe" "main.py" "%1"`."""
    frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    executable = executable or sys.executable
    if frozen:
        return f'"{executable}" "%1"'
    script = entry_script or Path(__file__).resolve().parent.parent / "main.py"
    return f'"{executable}" "{script}" "%1"'


def _winreg() -> ModuleType | None:
    try:
        import winreg  # yalniz Windows'ta vardir
    except ImportError:
        return None
    return winreg


class ProtocolRegistration:
    """`registry` testlerde sahte `winreg` ile degistirilir. Windows disinda `supported` False'tur."""

    def __init__(self, registry: ModuleType | None = None, command: str | None = None) -> None:
        self._registry = registry if registry is not None else _winreg()
        self._command = command or expected_command()

    @property
    def supported(self) -> bool:
        return self._registry is not None

    def is_registered(self) -> bool:
        """Kayit var ve bu uygulamanin guncel komutuna isaret ediyor mu? (Eski/tasinmis yol: False.)"""
        if self._registry is None:
            return False
        try:
            with self._registry.OpenKey(self._registry.HKEY_CURRENT_USER, _KEY + r"\shell\open\command") as key:
                value, _kind = self._registry.QueryValueEx(key, "")
        except OSError:
            return False
        return value == self._command

    def register(self) -> None:
        r = self._registry
        if r is None:
            raise OSError("Protokol kaydi yalniz Windows'ta desteklenir.")
        with r.CreateKey(r.HKEY_CURRENT_USER, _KEY) as key:
            r.SetValueEx(key, "", 0, r.REG_SZ, "URL:PKM Protocol")
            r.SetValueEx(key, "URL Protocol", 0, r.REG_SZ, "")
        with r.CreateKey(r.HKEY_CURRENT_USER, _KEY + r"\shell\open\command") as key:
            r.SetValueEx(key, "", 0, r.REG_SZ, self._command)

    def unregister(self) -> None:
        """Kaydi siler (yoksa sessizce gecer). Yalnizca `pkm` anahtarinin kendi alt anahtarlarini siler."""
        r = self._registry
        if r is None:
            return
        for sub in (r"\shell\open\command", r"\shell\open", r"\shell", ""):
            try:
                r.DeleteKey(r.HKEY_CURRENT_USER, _KEY + sub)
            except OSError:
                pass
