"""Uygulama güncelleme servisi: GitHub Releases üzerinden yeni sürüm denetimi,
kurulum dosyasını indirme, SHA-256 doğrulama ve kurulumu başlatma.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import logging
import os
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core.exceptions import InstallerBlockedError, UpdateError
from core.paths import update_download_dir, updates_file_path
from core.version import (
    INSTALLER_NAME_PREFIX,
    INSTALLER_PATTERN,
    RELEASE_REPO,
    __version__,
    format_version,
    parse_version,
)

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 15
_CHUNK_BYTES = 64 * 1024
_MAX_FILE_SIZE = 400 * 1024 * 1024  # 400 MB sınır

ProgressCallback = Callable[[int], None]


@dataclass(frozen=True)
class UpdateInfo:
    """Yayınlanmış yeni sürümün kullanıcıya gösterilen ve indirmek için gereken bilgileri."""

    version: str
    notes: str
    download_url: str
    size: int
    sha256: str | None
    asset_name: str
    html_url: str


def load_update_settings() -> dict[str, Any]:
    """Güncelleme ayarlarını updates.json dosyasından okur."""
    path = updates_file_path()
    if not path.exists():
        return {"auto_check": True, "skipped_version": None, "last_checked": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {
                "auto_check": bool(data.get("auto_check", True)),
                "skipped_version": data.get("skipped_version"),
                "last_checked": data.get("last_checked"),
            }
    except Exception as exc:
        logger.warning("Güncelleme ayarları okunamadı: %s", exc)
    return {"auto_check": True, "skipped_version": None, "last_checked": None}


def save_update_settings(settings: dict[str, Any]) -> None:
    """Güncelleme ayarlarını updates.json dosyasına kaydeder."""
    path = updates_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logger.warning("Güncelleme ayarları kaydedilemedi: %s", exc)


class UpdateService:
    """GitHub Releases ile güncelleme denetimi, indirme ve doğrulama servisi."""

    def __init__(
        self,
        current_version: str = __version__,
        repository: str = RELEASE_REPO,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self._current_version = current_version
        self._repository = repository
        self._opener = opener

    def check_for_update(self, ignore_skipped: bool = False) -> UpdateInfo | None:
        """Yeni sürüm varsa bilgisini döner; yoksa veya hata oluşursa None/UpdateError."""
        settings = load_update_settings()
        settings["last_checked"] = datetime.now().isoformat()
        save_update_settings(settings)

        release = self._fetch_latest_release()
        tag_name = str(release.get("tag_name", ""))
        latest = parse_version(tag_name)
        current = parse_version(self._current_version)

        if latest is None or current is None or latest <= current:
            return None

        latest_str = format_version(latest)
        if not ignore_skipped and settings.get("skipped_version") == latest_str:
            logger.info("Sürüm %s kullanıcı tarafından atlanmış.", latest_str)
            return None

        asset = self._find_installer_asset(release)
        asset_name = str(asset.get("name", ""))
        download_url = self._validated_download_url(str(asset.get("browser_download_url", "")))
        size = int(asset.get("size") or 0)

        # SHA-256'yı asset digest'inden ya da release'teki .sha256 dosyasından bul
        digest = str(asset.get("digest") or "")
        sha256 = digest.removeprefix("sha256:") if digest.startswith("sha256:") else None
        if not sha256:
            sha256 = self._fetch_sha256_from_release(release, asset_name)

        return UpdateInfo(
            version=latest_str,
            notes=str(release.get("body") or ""),
            download_url=download_url,
            size=size,
            sha256=sha256,
            asset_name=asset_name,
            html_url=str(release.get("html_url") or f"https://github.com/{self._repository}/releases/tag/{tag_name}"),
        )

    def download_installer(
        self,
        info: UpdateInfo,
        progress_callback: ProgressCallback | None = None,
    ) -> Path:
        """Kurulum dosyasını indirir ve SHA-256 doğrulaması yapar.
        
        Özet uyuşmazlığında veya eksik olduğunda dosya DERHAL silinir ve UpdateError fırlatılır.
        """
        target_dir = update_download_dir()
        target_dir.mkdir(parents=True, exist_ok=True)

        if not INSTALLER_PATTERN.match(info.asset_name):
            raise UpdateError(f"Güvenlik ihlali: Kurulum dosyası adı desene uymuyor ({info.asset_name})")

        self._validated_download_url(info.download_url)

        target = target_dir / info.asset_name
        try:
            received, calculated_sha = self._download_to(info, target, progress_callback)
            self._verify(info, received, calculated_sha)
        except UpdateError:
            target.unlink(missing_ok=True)
            raise
        except OSError as exc:
            target.unlink(missing_ok=True)
            raise UpdateError(f"Güncelleme indirilemedi: {exc}") from exc

        return target

    @staticmethod
    def launch_installer(installer: Path) -> None:
        """Kurulum dosyasını bağımsız süreç olarak başlatır."""
        if os.name != "nt":
            raise UpdateError("Otomatik güncelleme yalnızca Windows ortamında desteklenir.")

        if not installer.exists():
            raise FileNotFoundError(f"Kurulum dosyası bulunamadı: {installer}")

        log_path = installer.with_name("install.log")
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        cmd = [
            str(installer),
            "/SILENT",
            "/SUPPRESSMSGBOXES",
            "/CLOSEAPPLICATIONS",
            f"/LOG={log_path}",
        ]

        # 1. İlk deneme: CreateProcess (subprocess.Popen)
        try:
            subprocess.Popen(cmd, close_fds=True, creationflags=flags)
            return
        except OSError as exc:
            winerror = getattr(exc, "winerror", None)
            if winerror not in (4551, 1260):
                raise UpdateError(f"Kurulum başlatılamadı: {exc}") from exc

            # 2. İkinci deneme: Windows Gezgin çift tıklama yolu (ShellExecuteW)
            try:
                args_str = f"/SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /LOG=\"{log_path}\""
                ret = ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "open",
                    str(installer),
                    args_str,
                    str(installer.parent),
                    1,  # SW_SHOWNORMAL
                )
                if ret > 32:  # 32'den büyükse başarılı
                    return
            except Exception:
                pass

            raise InstallerBlockedError(
                f"Windows Akıllı Uygulama Denetimi (SAC) kurulum dosyasını engelledi (WinError {winerror})."
            )

    # ── Dahili Yardımcılar ─────────────────────────────────────────────────────

    def _open(self, url: str) -> Any:
        request = Request(
            url,
            headers={
                "User-Agent": f"KaynakYonetimPlatformu/{self._current_version}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            return self._opener(request, timeout=_TIMEOUT_SECONDS)
        except OSError as exc:
            raise UpdateError(f"Güncelleme sunucusuna ulaşılamadı: {exc}") from exc

    def _fetch_latest_release(self) -> dict[str, Any]:
        url = f"https://api.github.com/repos/{self._repository}/releases/latest"
        try:
            with self._open(url) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError) as exc:
            raise UpdateError(f"Sürüm bilgisi okunamadı: {exc}") from exc
        if not isinstance(payload, dict):
            raise UpdateError("Sürüm bilgisi beklenmeyen formatta.")
        return payload

    def _find_installer_asset(self, release: dict[str, Any]) -> dict[str, Any]:
        for asset in release.get("assets") or []:
            name = str(asset.get("name", ""))
            if INSTALLER_PATTERN.match(name):
                return asset
        raise UpdateError(f"Sürümde '{INSTALLER_NAME_PREFIX}-X.Y.Z.exe' kurulum dosyası bulunamadı.")

    def _fetch_sha256_from_release(self, release: dict[str, Any], installer_name: str) -> str | None:
        target_name = f"{installer_name}.sha256"
        sha_url = None
        for asset in release.get("assets") or []:
            if asset.get("name") == target_name:
                sha_url = asset.get("browser_download_url")
                break
        if not sha_url:
            return None
        try:
            with self._open(sha_url) as resp:
                text = resp.read().decode("utf-8").strip()
                parts = text.split()
                if parts:
                    return parts[0].lower()
        except Exception as exc:
            logger.warning(".sha256 özeti indirilemedi: %s", exc)
        return None

    def _validated_download_url(self, url: str) -> str:
        parsed = urlparse(url)
        expected_prefix = f"/{self._repository}/releases/download/"
        if (
            parsed.scheme != "https"
            or parsed.netloc not in ("github.com", "objects.githubusercontent.com")
            or not parsed.path.startswith(expected_prefix)
        ):
            raise UpdateError("Güvenlik ihlali: Güncelleme indirme adresi güvenilir değil.")
        return url

    def _download_to(
        self,
        info: UpdateInfo,
        target: Path,
        progress_callback: ProgressCallback | None,
    ) -> tuple[int, str]:
        hasher = hashlib.sha256()
        received = 0
        with self._open(info.download_url) as response, target.open("wb") as out:
            while chunk := response.read(_CHUNK_BYTES):
                out.write(chunk)
                hasher.update(chunk)
                received += len(chunk)
                if received > _MAX_FILE_SIZE:
                    raise UpdateError("İndirilen dosya izin verilen 400 MB sınırını aştı.")
                if progress_callback is not None and info.size > 0:
                    pct = min(100, int((received / info.size) * 100))
                    progress_callback(pct)
        return received, hasher.hexdigest().lower()

    @staticmethod
    def _verify(info: UpdateInfo, received: int, calculated_sha: str) -> None:
        if info.size > 0 and received != info.size:
            raise UpdateError(f"İndirilen dosya eksik; beklenen {info.size} bayt, alınan {received} bayt.")

        # Zorunlu SHA-256: Özet yoksa güncelleme kesinlikle reddedilir!
        if not info.sha256:
            raise UpdateError("Sürümde SHA-256 doğrulama özeti bulunamadı; güvenlik nedeniyle güncelleme reddedildi.")

        if calculated_sha.lower() != info.sha256.lower():
            raise UpdateError(
                f"Güvenlik ihlali: SHA-256 özeti eşleşmiyor!\n"
                f"Beklenen: {info.sha256}\nHesaplanan: {calculated_sha}"
            )
