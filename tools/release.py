"""Sürüm yayınlama ve etiketleme yardımcısı.

Kullanım:
  python tools/release.py 1.0.1
  python tools/release.py --check-tag v1.0.1 (CI'da doğrulama için)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "core" / "version.py"
README_FILE = ROOT / "README.md"


def run_git(*args: str, check: bool = True) -> str:
    """Git komutunu çalıştırır ve çıktısını döner."""
    res = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=check)
    return res.stdout.strip()


def check_tag_matches_version(tag: str) -> None:
    """CI adımı: Verilen git etiketinin core/version.py ile birebir eşleştiğini doğrular."""
    from core.version import __version__

    clean_tag = tag.strip().lstrip("v")
    if clean_tag != __version__:
        print(f"[HATA] Git etiketi ({tag}) ile core/version.py sürümü ({__version__}) eşleşmiyor!")
        sys.exit(1)
    print(f"[DOĞRULANDI] Git etiketi ({tag}) ve core/version.py sürümü ({__version__}) uyumlu.")


def update_version_file(new_version: str) -> None:
    """core/version.py içindeki __version__ satırını günceller."""
    content = VERSION_FILE.read_text(encoding="utf-8")
    new_content, count = re.subn(
        r'__version__\s*=\s*["\'][^"\']+["\']',
        f'__version__ = "{new_version}"',
        content,
    )
    if count == 0:
        raise ValueError("core/version.py içinde __version__ satırı bulunamadı!")
    VERSION_FILE.write_text(new_content, encoding="utf-8")
    print(f"[GÜNCELLENDİ] core/version.py -> {new_version}")


def update_readme_badge(new_version: str) -> None:
    """README.md içindeki sürüm rozeti varsa günceller."""
    if not README_FILE.exists():
        return
    content = README_FILE.read_text(encoding="utf-8")
    # v1.0.0 rozet deseni örneği
    pattern = r'(badge/version-v?)[0-9.]+(-[a-zA-Z0-9]+)'
    if re.search(pattern, content):
        new_content = re.sub(pattern, rf'\g<1>{new_version}\g<2>', content)
        README_FILE.write_text(new_content, encoding="utf-8")
        print(f"[GÜNCELLENDİ] README.md rozeti -> {new_version}")


def main() -> None:
    parser = argparse.ArgumentParser(description="KaynakYonetimPlatformu Sürüm Aracı")
    parser.add_argument("version", nargs="?", help="Yayınlanacak yeni sürüm (MAJOR.MINOR.PATCH)")
    parser.add_argument("--check-tag", help="CI kontrolü: etiket ile version.py sürümünü doğrular")
    args = parser.parse_args()

    if args.check_tag:
        check_tag_matches_version(args.check_tag)
        return

    if not args.version:
        parser.print_help()
        sys.exit(1)

    new_ver = args.version.strip().lstrip("v")
    parts = new_ver.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        print(f"[HATA] Sürüm numarası MAJOR.MINOR.PATCH biçiminde olmalıdır (örn: 1.0.1), verilen: {new_ver}")
        sys.exit(1)

    # 1. Git çalışma dizini temiz mi?
    status = run_git("status", "--porcelain")
    if status:
        print("[HATA] Git çalışma dizini temiz değil! Lütfen değişiklikleri commit edin veya temizleyin.")
        print(status)
        sys.exit(1)

    # 2. Dal main mi?
    current_branch = run_git("rev-parse", "--abbrev-ref", "HEAD")
    if current_branch != "main":
        print(f"[UYARI] Şu anki dal '{current_branch}' (yayınlar genellikle 'main' dalından yapılır).")

    # 3. Dosyaları güncelle
    update_version_file(new_ver)
    update_readme_badge(new_ver)

    # 4. Commit ve Etiket
    tag_name = f"v{new_ver}"
    run_git("add", "core/version.py")
    if README_FILE.exists():
        run_git("add", "README.md")

    commit_msg = f"chore(release): {tag_name}"
    run_git("commit", "-m", commit_msg)
    run_git("tag", "-a", tag_name, "-m", f"Release {tag_name}")

    print("\n" + "=" * 70)
    print(f"Sürüm {tag_name} başarıyla oluşturuldu!")
    print("Yayını başlatmak için şu komutları sırayla çalıştırın:")
    print(f"  git push origin {current_branch}")
    print(f"  git push origin {tag_name}")
    print("\n(NOT: 'git push --follow-tags' KULLANMAYIN; hafif etiketleri göndermeyebilir)")
    print("=" * 70)


if __name__ == "__main__":
    main()
