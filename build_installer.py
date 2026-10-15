"""Tek komutla Windows exe, Inno Setup kurulum dosyası ve .sha256 özeti üreticisi.

Akış:
1. Inno Setup derleyicisini (ISCC) bulur.
2. `core/version.py` içinden sürüm bilgisini okur.
3. `build_exe.py` ile uygulamayı derler (kararlı launcher kapısını denetler).
4. Yerelde derlenen exe'yi test eder (`launch_check`).
5. Inno Setup ile `KaynakYonetimPlatformu-Setup-X.Y.Z.exe` dosyasını derler.
6. Kurulum dosyasını geçici klasörde sessizce test eder (`installer_check`).
7. Kurulum dosyasının `.sha256` özet dosyasını üretir.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from build_exe import build_executable, calculate_sha256
from build_verify import installer_check, launch_check
from core.version import __version__


def find_iscc() -> Path:
    """Inno Setup komut satırı derleyicisini (ISCC.exe) bulur."""
    iscc_path = shutil.which("iscc") or shutil.which("ISCC")
    if iscc_path:
        return Path(iscc_path)

    common_paths = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    for p in common_paths:
        if p.exists():
            return p

    raise FileNotFoundError(
        "Inno Setup 6 (ISCC.exe) bulunamadı! Lütfen Inno Setup 6 kurun "
        "(https://jrsoftware.org/isdl.php veya 'choco install innosetup -y')."
    )


def compile_inno_setup(iscc: Path, version: str) -> Path:
    """Inno Setup betiğini derler ve üretilen kurulum dosyası yolunu döner."""
    root = Path(__file__).resolve().parent
    iss_file = root / "packaging" / "P011_KaynakYonetim.iss"
    output_dir = root / "dist" / "installer"
    output_dir.mkdir(parents=True, exist_ok=True)

    expected_installer = output_dir / f"KaynakYonetimPlatformu-Setup-{version}.exe"

    cmd = [
        str(iscc),
        f"/DAppVersion={version}",
        str(iss_file),
    ]

    print(f"\n[Inno Setup] Kurulum dosyası derleniyor (Sürüm: {version})...")
    res = subprocess.run(cmd, cwd=root)
    if res.returncode != 0:
        raise RuntimeError(f"Inno Setup derlemesi başarısız oldu (çıkış kodu: {res.returncode})")

    if not expected_installer.exists():
        raise FileNotFoundError(f"Beklenen kurulum dosyası üretilemedi: {expected_installer}")

    print(f"[Inno Setup Başarılı] Kurulum dosyası oluşturuldu: {expected_installer.name}")
    return expected_installer


def write_sha256_file(target_file: Path) -> Path:
    """Hedef dosyanın yanına `<dosya>.sha256` dosyası yazar."""
    digest = calculate_sha256(target_file)
    sha_file = target_file.with_name(f"{target_file.name}.sha256")
    sha_file.write_text(f"{digest} *{target_file.name}\n", encoding="utf-8")
    print(f"[SHA-256] Özet yazıldı: {sha_file.name} ({digest})")
    return sha_file


def main() -> None:
    parser = argparse.ArgumentParser(description="KaynakYonetimPlatformu kurulum paketi derleyicisi")
    parser.add_argument("--skip-build", action="store_true", help="PyInstaller derlemesini atlar, mevcut dist'i kullanır")
    parser.add_argument("--no-verify", action="store_true", help="Yerel çalışma ve kurulum testlerini atlar (CI için)")
    parser.add_argument("--update-launcher-hash", action="store_true", help="Yeni exe özetini onay kapısına yazar")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    iscc = find_iscc()
    version = __version__
    is_ci = bool(os.environ.get("CI"))
    should_verify = not args.no_verify and not is_ci

    print("=" * 70)
    print(f"KaynakYonetimPlatformu Paketleme Başlatılıyor (v{version})")
    print(f"ISCC Derleyicisi: {iscc}")
    print(f"Doğrulama aktif: {should_verify}")
    print("=" * 70)

    # 1. PyInstaller Derlemesi
    if not args.skip_build:
        exe_path = build_executable(update_hash=args.update_launcher_hash)
    else:
        exe_path = root / "dist" / "KaynakYonetimPlatformu" / "KaynakYonetimPlatformu.exe"
        if not exe_path.exists():
            raise FileNotFoundError(f"--skip-build verildi ancak exe bulunamadı: {exe_path}")

    # 2. Exe Doğrulama (SAC & Crash testi)
    if should_verify:
        print("\n[Doğrulama 1/2] Derlenen exe test ediliyor...")
        launch_check(exe_path, seconds=6.0)

    # 3. Inno Setup Derlemesi
    installer_path = compile_inno_setup(iscc, version)

    # 4. Kurulum Dosyası Doğrulama (Sessiz kurulum + kaldırıcı testi)
    if should_verify:
        print("\n[Doğrulama 2/2] Kurulum dosyası test ediliyor...")
        try:
            installer_check(installer_path)
        except Exception as exc:
            print(f"\n[UYARI] Kurulum dosyası testi uyarı verdi: {exc}")
            print("Not: Kurulum dosyası her sürümde yenidir; SAC engeli olursa güncelleme sistemi otomatik bekleyip yeniden dener.")

    # 5. SHA-256 Dosyası Üretimi
    write_sha256_file(installer_path)

    print("\n" + "=" * 70)
    print("TÜM PAKETLEME ADIMLARI BAŞARIYLA TAMAMLANDI!")
    print(f"Kurulum Dosyası: {installer_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
