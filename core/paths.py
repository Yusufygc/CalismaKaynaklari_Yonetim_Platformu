"""Uygulama yol çözücüleri.

PyInstaller ile paketlendiğinde (``sys.frozen``) salt-okunur kaynaklar
``sys._MEIPASS`` altında, kullanıcıya ait yazılabilir veriler ise platforma
özgü "AppData" dizininde tutulur. Bu modül her iki ortam için tek noktadan
yol üretir; uygulama içinde ``__file__`` tabanlı manuel hesaplamaların
yerini alır.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_APP_DIR_NAME = "PKM"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _frozen_base() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(sys.executable).resolve().parent


def _source_base() -> Path:
    # Proje kökü (bu dosya core/paths.py, kök core/'un bir üstü)
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """Salt-okunur paket içi kaynak (QSS, ikon vb.) yolu."""
    base = _frozen_base() if is_frozen() else _source_base()
    return base.joinpath(*parts)


def user_data_dir() -> Path:
    """Yazılabilir kullanıcı verisi dizini (SQLite, log)."""
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    target = root / _APP_DIR_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target


def pdf_storage_dir() -> Path:
    """Yerel PDF ice aktarimlarinin kopyalandigi yazilabilir dizin (%APPDATA%/PKM/pdfs)."""
    target = user_data_dir() / "pdfs"
    target.mkdir(parents=True, exist_ok=True)
    return target
