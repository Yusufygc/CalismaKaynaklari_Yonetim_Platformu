"""Uygulamayla birlikte gelen yazi tipleri (`assets/fonts/*.ttf`, SIL OFL; bkz. assets/fonts/LICENSES.txt).

Qt'ye uygulama yazi tipi olarak kaydedilir; boylece `Qt.fontFamilies()` bunlari da listeler ve Ayarlar > Gorunum'deki
yazi tipi ciftleri (`qml/theme/fonts.js`) bilgisayarda kurulu olmasalar da bunlari kullanir. Degisken yazi tipleri
(Inter, EB Garamond, Source Sans 3...) tek dosyada tum agirliklari tasir."""
from pathlib import Path

from core.logger import log
from core.paths import resource_path


def bundled_font_dir() -> Path:
    return resource_path("assets", "fonts")


def register_bundled_fonts(directory: Path | None = None) -> list[str]:
    """Klasordeki tum .ttf dosyalarini kaydeder; kaydedilen yazi tipi ailelerini (tekrarsiz) doner. Bir dosya yuklenemezse
    uyari yazilir ve digerleri yuklenmeye devam eder (yazi tipi eksikligi uygulamayi durdurmaz)."""
    from PySide6.QtGui import QFontDatabase

    folder = directory or bundled_font_dir()
    families: list[str] = []
    for path in sorted(folder.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            log.warning("Yazi tipi yuklenemedi: %s", path.name)
            continue
        families += [name for name in QFontDatabase.applicationFontFamilies(font_id) if name not in families]
    return families
