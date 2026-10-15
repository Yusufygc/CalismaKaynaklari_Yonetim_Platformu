import hashlib
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.exceptions import UpdateError
from services.update_service import UpdateInfo, UpdateService


class MockResponse:
    def __init__(self, data: bytes) -> None:
        self._bio = io.BytesIO(data)

    def read(self, chunk_size: int = -1) -> bytes:
        return self._bio.read(chunk_size)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_check_for_update_newer_version_available():
    release_payload = {
        "tag_name": "v1.1.0",
        "body": "Yeni özellikler eklendi.",
        "html_url": "https://github.com/Yusufygc/CalismaKaynaklari_Yonetim_Platformu/releases/tag/v1.1.0",
        "assets": [
            {
                "name": "KaynakYonetimPlatformu-Setup-1.1.0.exe",
                "browser_download_url": "https://github.com/Yusufygc/CalismaKaynaklari_Yonetim_Platformu/releases/download/v1.1.0/KaynakYonetimPlatformu-Setup-1.1.0.exe",
                "size": 1024,
                "digest": "sha256:abc12345def67890abc12345def67890abc12345def67890abc12345def67890",
            }
        ],
    }

    def fake_opener(req, timeout=10):
        return MockResponse(json.dumps(release_payload).encode("utf-8"))

    service = UpdateService(
        current_version="1.0.0",
        repository="Yusufygc/CalismaKaynaklari_Yonetim_Platformu",
        opener=fake_opener,
    )
    info = service.check_for_update(ignore_skipped=True)
    assert info is not None
    assert info.version == "1.1.0"
    assert info.size == 1024
    assert info.sha256 == "abc12345def67890abc12345def67890abc12345def67890abc12345def67890"


def test_check_for_update_same_or_older_version():
    release_payload = {
        "tag_name": "v1.0.0",
        "assets": [{"name": "KaynakYonetimPlatformu-Setup-1.0.0.exe"}],
    }

    def fake_opener(req, timeout=10):
        return MockResponse(json.dumps(release_payload).encode("utf-8"))

    service = UpdateService(
        current_version="1.0.0",
        repository="Yusufygc/CalismaKaynaklari_Yonetim_Platformu",
        opener=fake_opener,
    )
    assert service.check_for_update(ignore_skipped=True) is None


def test_check_for_update_prerelease_ignored():
    release_payload = {
        "tag_name": "v2.0.0-rc1",
        "assets": [{"name": "KaynakYonetimPlatformu-Setup-2.0.0-rc1.exe"}],
    }

    def fake_opener(req, timeout=10):
        return MockResponse(json.dumps(release_payload).encode("utf-8"))

    service = UpdateService(
        current_version="1.0.0",
        repository="Yusufygc/CalismaKaynaklari_Yonetim_Platformu",
        opener=fake_opener,
    )
    assert service.check_for_update(ignore_skipped=True) is None


def test_download_installer_rejects_untrusted_url(tmp_path):
    info = UpdateInfo(
        version="1.1.0",
        notes="Notlar",
        download_url="https://evil.com/releases/download/v1.1.0/KaynakYonetimPlatformu-Setup-1.1.0.exe",
        size=10,
        sha256="abc",
        asset_name="KaynakYonetimPlatformu-Setup-1.1.0.exe",
        html_url="https://github.com",
    )
    service = UpdateService()
    with pytest.raises(UpdateError, match="güvenilir değil"):
        service.download_installer(info)


def test_download_installer_rejects_invalid_filename(tmp_path):
    info = UpdateInfo(
        version="1.1.0",
        notes="Notlar",
        download_url="https://github.com/Yusufygc/CalismaKaynaklari_Yonetim_Platformu/releases/download/v1.1.0/Setup.exe",
        size=10,
        sha256="abc",
        asset_name="Setup.exe",
        html_url="https://github.com",
    )
    service = UpdateService()
    with pytest.raises(UpdateError, match="desene uymuyor"):
        service.download_installer(info)


def test_download_installer_sha256_verification_success(tmp_path, monkeypatch):
    content = b"Binary installer payload content"
    digest = hashlib.sha256(content).hexdigest().lower()

    info = UpdateInfo(
        version="1.1.0",
        notes="",
        download_url="https://github.com/Yusufygc/CalismaKaynaklari_Yonetim_Platformu/releases/download/v1.1.0/KaynakYonetimPlatformu-Setup-1.1.0.exe",
        size=len(content),
        sha256=digest,
        asset_name="KaynakYonetimPlatformu-Setup-1.1.0.exe",
        html_url="https://github.com",
    )

    monkeypatch.setattr("services.update_service.update_download_dir", lambda: tmp_path)
    service = UpdateService(opener=lambda req, timeout=10: MockResponse(content))

    downloaded = service.download_installer(info)
    assert downloaded.exists()
    assert downloaded.read_bytes() == content


def test_download_installer_sha256_mismatch_deletes_file(tmp_path, monkeypatch):
    content = b"Binary content"
    wrong_digest = "0000000000000000000000000000000000000000000000000000000000000000"

    info = UpdateInfo(
        version="1.1.0",
        notes="",
        download_url="https://github.com/Yusufygc/CalismaKaynaklari_Yonetim_Platformu/releases/download/v1.1.0/KaynakYonetimPlatformu-Setup-1.1.0.exe",
        size=len(content),
        sha256=wrong_digest,
        asset_name="KaynakYonetimPlatformu-Setup-1.1.0.exe",
        html_url="https://github.com",
    )

    monkeypatch.setattr("services.update_service.update_download_dir", lambda: tmp_path)
    service = UpdateService(opener=lambda req, timeout=10: MockResponse(content))

    with pytest.raises(UpdateError, match="SHA-256 özeti eşleşmiyor"):
        service.download_installer(info)

    target_file = tmp_path / info.asset_name
    assert not target_file.exists()


def test_download_installer_rejects_missing_sha256(tmp_path, monkeypatch):
    content = b"Binary content"
    info = UpdateInfo(
        version="1.1.0",
        notes="",
        download_url="https://github.com/Yusufygc/CalismaKaynaklari_Yonetim_Platformu/releases/download/v1.1.0/KaynakYonetimPlatformu-Setup-1.1.0.exe",
        size=len(content),
        sha256=None,  # özet yok
        asset_name="KaynakYonetimPlatformu-Setup-1.1.0.exe",
        html_url="https://github.com",
    )

    monkeypatch.setattr("services.update_service.update_download_dir", lambda: tmp_path)
    service = UpdateService(opener=lambda req, timeout=10: MockResponse(content))

    with pytest.raises(UpdateError, match="SHA-256 doğrulama özeti bulunamadı"):
        service.download_installer(info)
