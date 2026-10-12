"""Kullaniciya ait kalici ayarlar (ornegin Obsidian vault klasoru): `%APPDATA%/PKM/user_settings.json`.

Veritabani disinda tutulur: yedekten geri yuklenen/degistirilen bir veritabani, kullanicinin makinesindeki klasor
secimini bozmasin. Yazim atomiktir (gecici dosya + `os.replace`); bozuk dosya yok sayilir ve kenara alinir."""
import json
import os
from pathlib import Path
from typing import Any

from core.logger import log
from core.paths import user_data_dir

_FILE_NAME = "user_settings.json"


def default_settings_path() -> Path:
    return user_data_dir() / _FILE_NAME


class UserSettings:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._values: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        except OSError as exc:
            log.warning("Kullanici ayarlari okunamadi: %s", exc)
            return {}
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except ValueError:
            pass
        log.warning("Kullanici ayarlari bozuk, yok sayildi: %s", self._path)
        try:
            os.replace(self._path, self._path.with_suffix(".corrupt"))
        except OSError:
            pass
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Degeri kaydeder (None = anahtari siler). Yazilamazsa False doner ve bellekteki deger degismez."""
        updated = dict(self._values)
        if value is None:
            updated.pop(key, None)
        else:
            updated[key] = value
        temporary = self._path.with_name(self._path.name + ".tmp")
        try:
            temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, self._path)
        except OSError as exc:
            log.warning("Kullanici ayarlari yazilamadi: %s", exc)
            return False
        self._values = updated
        return True
