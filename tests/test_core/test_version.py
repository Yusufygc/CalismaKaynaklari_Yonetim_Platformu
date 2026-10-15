import pytest
from core.version import (
    INSTALLER_PATTERN,
    RELEASE_REPO,
    __version__,
    format_version,
    parse_version,
)


def test_current_version_format():
    assert parse_version(__version__) is not None
    assert RELEASE_REPO == "Yusufygc/CalismaKaynaklari_Yonetim_Platformu"


def test_parse_version_valid():
    assert parse_version("1.0.0") == (1, 0, 0)
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("v10.200.30") == (10, 200, 30)


def test_parse_version_pre_release_ignored():
    assert parse_version("1.0.0-rc1") is None
    assert parse_version("v2.1.0-beta.2") is None
    assert parse_version("v1.0.0-alpha") is None


def test_parse_version_invalid():
    assert parse_version("") is None
    assert parse_version("not_a_version") is None
    assert parse_version("1.2") is None


def test_format_version():
    assert format_version((1, 2, 3)) == "1.2.3"
    assert format_version((2, 0, 10)) == "2.0.10"


def test_installer_pattern():
    assert INSTALLER_PATTERN.match("KaynakYonetimPlatformu-Setup-1.0.0.exe")
    assert INSTALLER_PATTERN.match("KaynakYonetimPlatformu-Setup-2.15.3.exe")
    assert not INSTALLER_PATTERN.match("KaynakYonetimPlatformu-Setup.exe")
    assert not INSTALLER_PATTERN.match("Setup-1.0.0.exe")
    assert not INSTALLER_PATTERN.match("Malicious-Setup-1.0.0.exe")
