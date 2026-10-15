from pathlib import Path
import pytest
from build_exe import LAUNCHER_EPOCH, calculate_sha256, check_launcher_hash

ROOT = Path(__file__).resolve().parent.parent.parent


def test_launcher_script_exists_and_content():
    launcher = ROOT / "packaging" / "launcher.py"
    assert launcher.exists()
    content = launcher.read_text(encoding="utf-8")
    assert "BU DOSYAYI DEĞİŞTİRME" in content or "BU DOSYAYI DEGISTIRME" in content
    assert "from main import main" in content
    assert "main()" in content


def test_launcher_version_info_fixed():
    version_file = ROOT / "packaging" / "launcher_version_info.txt"
    assert version_file.exists()
    content = version_file.read_text(encoding="utf-8")
    # Sabit 1.0.0.0 PE bilgisi Smart App Control itibarını korur
    assert "1.0.0.0" in content
    assert "FileVersion" in content
    assert "ProductVersion" in content


def test_inno_setup_script_settings():
    iss_file = ROOT / "packaging" / "P011_KaynakYonetim.iss"
    assert iss_file.exists()
    content = iss_file.read_text(encoding="utf-8")

    assert "PrivilegesRequired=lowest" in content
    assert "CloseApplications=yes" in content
    assert "Check: RelaunchAfterUpdate" in content
    assert "RelaunchAfterUpdate: Boolean" in content
    assert "WizardSilent and not HasParam('/VERYSILENT')" in content
    assert "AppId={{7470CA3F-5001-4DFC-BFF7-5535C9C85DAD}}" in content


def test_launcher_epoch_is_constant():
    assert isinstance(LAUNCHER_EPOCH, int)
    assert LAUNCHER_EPOCH == 1700000000


def test_check_launcher_hash_gate_behavior(tmp_path, monkeypatch):
    test_exe = tmp_path / "dist" / "KaynakYonetimPlatformu" / "KaynakYonetimPlatformu.exe"
    test_exe.parent.mkdir(parents=True)
    test_exe.write_bytes(b"Fake executable bytes for test")

    hash_file = tmp_path / "packaging" / "launcher.sha256"

    # 1. Dosya yokken exit(1) atmalı
    with pytest.raises(SystemExit):
        check_launcher_hash(test_exe, update=False)

    # 2. update=True iken kaydetmeli
    assert check_launcher_hash(test_exe, update=True) is True
    assert hash_file.exists()

    # 3. Hash doğru iken True dönmeli
    assert check_launcher_hash(test_exe, update=False) is True

    # 4. Hash bozulunca exit(1) atmalı
    hash_file.write_text("0000000000000000000000000000000000000000000000000000000000000000 *KaynakYonetimPlatformu.exe\n")
    with pytest.raises(SystemExit):
        check_launcher_hash(test_exe, update=False)
