"""PyInstaller ile kararlı (deterministic) Windows exe derleme betiği.

Akıllı Uygulama Denetimi (Smart App Control - SAC) ve SmartScreen engellerini
önlemek için çalıştırılabilir launcher dosyasının SHA-256 özeti her sürümde
sabit tutulur. Python kodları `_internal` altında `.pyc` olarak saklanır.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

# launcher.py docstring veya PyInstaller sürümü değişmedikçe bu değer değiştirilmez.
LAUNCHER_EPOCH = 1700000000


def calculate_sha256(file_path: Path) -> str:
    """Belirtilen dosyanın SHA-256 özetini hesaplar."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(64 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def check_launcher_hash(exe_path: Path, update: bool = False) -> bool:
    """Derlenen exe'nin SHA-256 özetini packaging/launcher.sha256 ile karşılaştırır.
    
    Eşleşirse True döner. Farklıysa veya dosya yoksa:
    - update=True ise yeni özeti kaydeder ve True döner.
    - update=False ise yayını ve derlemeyi durdurur (SystemExit).
    """
    hash_file = exe_path.parents[2] / "packaging" / "launcher.sha256"
    actual_hash = calculate_sha256(exe_path)

    if update:
        hash_file.parent.mkdir(parents=True, exist_ok=True)
        hash_file.write_text(f"{actual_hash} *{exe_path.name}\n", encoding="utf-8")
        print(f"[KAPI GÜNCELLENDİ] Yeni onaylı launcher özeti kaydedildi: {actual_hash}")
        return True

    if not hash_file.exists():
        print("\n" + "=" * 70)
        print("[HATA] packaging/launcher.sha256 dosyası bulunamadı!")
        print(f"Derlenen exe özeti: {actual_hash}")
        print("Bu özeti onaylamak için şu komutu çalıştırın:")
        print("  python build_installer.py --update-launcher-hash")
        print("=" * 70 + "\n")
        sys.exit(1)

    content = hash_file.read_text(encoding="utf-8").strip().split()
    expected_hash = content[0].lower() if content else ""

    if actual_hash != expected_hash:
        print("\n" + "=" * 70)
        print("[GÜVENLİK KAPISI: ÖZET DEĞİŞTİ]")
        print("Derlenen exe özeti onaylanan özet ile eşleşmiyor!")
        print(f"Beklenen (onaylı): {expected_hash}")
        print(f"Üretilen (yeni)   : {actual_hash}")
        print("\nNedenler:")
        print("- Python veya PyInstaller sürümü değişmiş olabilir.")
        print("- packaging/launcher.py veya launcher_version_info.txt içeriği değişmiş olabilir.")
        print("- Satır sonları (CRLF/LF) farklılaşmış olabilir.")
        print("\nEğer bu değişikliği BİLEREK yaptıysanız ve bu makinede test ettiyseniz:")
        print("  python build_installer.py --update-launcher-hash")
        print("=" * 70 + "\n")
        sys.exit(1)

    print(f"[KAPI GEÇTİ] Kararlı exe özeti onaylananla aynı ({actual_hash[:16]}...)")
    return True


def build_executable(update_hash: bool = False, clean: bool = True) -> Path:
    """PyInstaller çalıştırarak onedir modunda uygulamayı derler."""
    root = Path(__file__).resolve().parent
    launcher_script = root / "packaging" / "launcher.py"
    version_file = root / "packaging" / "launcher_version_info.txt"
    dist_dir = root / "dist"
    exe_path = dist_dir / "KaynakYonetimPlatformu" / "KaynakYonetimPlatformu.exe"

    if not launcher_script.exists():
        raise FileNotFoundError(f"Giriş betiği bulunamadı: {launcher_script}")
    if not version_file.exists():
        raise FileNotFoundError(f"Sürüm kaynak dosyası bulunamadı: {version_file}")

    # Deterministik derleme: PE zaman damgasını sabitle
    os.environ["SOURCE_DATE_EPOCH"] = str(LAUNCHER_EPOCH)
    # PyInstaller önbelleği için
    os.environ["PYTHONHASHSEED"] = "1"

    # PyInstaller argümanları
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(launcher_script),
        f"--paths={root}",
        "--name=KaynakYonetimPlatformu",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--noupx",
        "--debug=noarchive",  # modülleri .pyc olarak _internal altına çıkar
        f"--version-file={version_file}",
        # Veri klasörleri
        f"--add-data={root / 'qml'};qml",
        f"--add-data={root / 'assets'};assets",
        f"--add-data={root / 'alembic.ini'};.",
        f"--add-data={root / 'migrations'};migrations",
        # Gizli/dinamik modüller
        "--collect-submodules=core",
        "--collect-submodules=services",
        "--collect-submodules=workers",
        "--collect-submodules=models",
        "--collect-submodules=repositories",
        "--collect-submodules=controllers",
        "--collect-submodules=utils",
        "--collect-submodules=pdfkit",
        "--collect-submodules=alembic",
        "--collect-data=alembic",
        "--collect-submodules=sqlalchemy.dialects.sqlite",
        "--collect-submodules=qtawesome",
        "--hidden-import=logging.config",
        "--hidden-import=sqlite3",
    ]

    # Uygulama ikonu (Windows Gezgini, Görev Çubuğu ve EXE kaynağı için çok boyutlu ICO)
    icon_file = root / "assets" / "icon.ico"
    if icon_file.exists():
        cmd.append(f"--icon={icon_file}")

    if clean:
        cmd.append("--clean")

    print("[1/2] PyInstaller derlemesi başlatılıyor...")
    result = subprocess.run(cmd, cwd=root)
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller derlemesi başarısız oldu (çıkış kodu: {result.returncode})")

    if not exe_path.exists():
        raise FileNotFoundError(f"Derlenen exe bulunamadı: {exe_path}")

    print("[2/2] Exe özet kapısı denetleniyor...")
    check_launcher_hash(exe_path, update=update_hash)
    return exe_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KaynakYonetimPlatformu PyInstaller derleyicisi")
    parser.add_argument("--update-launcher-hash", action="store_true", help="Yeni exe özetini onay kapısına yazar")
    parser.add_argument("--no-clean", action="store_true", help="Derleme öncesi geçici klasörleri temizlemez")
    args = parser.parse_args()

    build_executable(update_hash=args.update_launcher_hash, clean=not args.no_clean)
