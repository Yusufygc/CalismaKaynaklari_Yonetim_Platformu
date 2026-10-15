"""Surum ve depo bilgisi -- tek dogruluk kaynagi.

Surum numarasi MAJOR.MINOR.PATCH bicimindedir.
CI/CD release is akisi, etiket ile bu dosyadaki `__version__` eslesmesini dogrular.
exe'nin Windows PE surum kaynagi (packaging/launcher_version_info.txt) Smart App Control
itibarini korumak icin bilerek sabit 1.0.0.0 olarak tutulur; urun surumu bu dosyada ve
kurulum dosyasinda gorunur.
"""
from __future__ import annotations

import re

__version__ = "1.0.0"

RELEASE_REPO = "Yusufygc/CalismaKaynaklari_Yonetim_Platformu"
APP_NAME = "KaynakYonetimPlatformu"
INSTALLER_NAME_PREFIX = "KaynakYonetimPlatformu-Setup"
INSTALLER_PATTERN = re.compile(r"^KaynakYonetimPlatformu-Setup-(\d+\.\d+\.\d+)\.exe$")

_VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_version(text: str) -> tuple[int, int, int] | None:
    """`v1.2.3` ya da `1.2.3` bicimini sayisal 3'lu demete cevirir.
    On surumler (-rc1, -beta vb.) None doner ve guncelleyici tarafindan yok sayilir.
    """
    if not text:
        return None
    match = _VERSION_PATTERN.match(text.strip())
    if match is None:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def format_version(version_tuple: tuple[int, int, int]) -> str:
    """Sayisal 3'lu demeti 'MAJOR.MINOR.PATCH' dizesine cevirir."""
    return ".".join(str(n) for n in version_tuple)
