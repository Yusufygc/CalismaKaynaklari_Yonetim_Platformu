"""Derleme ve kurulum doğrulama araçları (bağımsız, yalnızca standart kütüphane).

İmzasız Windows çalıştırılabilir dosyalarını (exe, kurulum dosyası, kaldırıcı)
Akıllı Uygulama Denetimi (SAC) ve çalışma kararlılığı açısından test eder.
Kullanıcının mevcut gerçek sistem kaydını (Registry/Kısayollar) korumak için
yedekleme/geri yükleme mekanizması içerir.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import winreg
from pathlib import Path

APP_ID = "{7470CA3F-5001-4DFC-BFF7-5535C9C85DAD}"


def launch_check(exe_path: Path, seconds: float = 6.0) -> None:
    """Exe'yi başlatır; SAC engeli olup olmadığını ve çalıştığını doğrular."""
    if not exe_path.exists():
        raise FileNotFoundError(f"Doğrulanacak dosya bulunamadı: {exe_path}")

    env = os.environ.copy()
    env["PKM_NO_UPDATE_CHECK"] = "1"  # test sırasında ağa çıkmasın

    print(f"  [Doğrulama] Başlatılıyor ({seconds}s izleme): {exe_path.name}")
    try:
        proc = subprocess.Popen([str(exe_path)], env=env)
    except OSError as exc:
        winerror = getattr(exc, "winerror", None)
        if winerror in (4551, 1260):
            raise RuntimeError(f"Akıllı Uygulama Denetimi (SAC) dosyayı engelledi (WinError {winerror}): {exe_path}") from exc
        raise RuntimeError(f"Dosya başlatılamadı: {exc}") from exc

    try:
        start_time = time.time()
        while time.time() - start_time < seconds:
            ret = proc.poll()
            if ret is not None:
                if ret != 0:
                    raise RuntimeError(f"Uygulama beklenmedik şekilde çöktü (çıkış kodu: {ret})")
                break
            time.sleep(0.5)
        print("  [Doğrulama Başarılı] Exe normal şekilde çalıştı ve SAC engeli almadı.")
    finally:
        if proc.poll() is None:
            # Süreç ağacını zorla sonlandır
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)


class RegistrationGuard:
    """Gerçek kurulum kaydını Inno deneme kurulumundan koruyan yedekleyici."""

    def __init__(self, app_id: str = APP_ID) -> None:
        self.app_id = app_id
        self.sub_key = f"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_id}_is1"
        self.backup_values: dict[str, tuple[object, int]] = {}
        self.had_key = False

    def __enter__(self) -> RegistrationGuard:
        self.save()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.restore()

    def save(self) -> None:
        """Mevcut registry kayıtlarını belleğe yedekler."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.sub_key, 0, winreg.KEY_READ) as key:
                self.had_key = True
                i = 0
                while True:
                    try:
                        name, val, val_type = winreg.EnumValue(key, i)
                        self.backup_values[name] = (val, val_type)
                        i += 1
                    except OSError:
                        break
        except FileNotFoundError:
            self.had_key = False

    def restore(self) -> None:
        """Kayıtları önceki durumuna geri getirir."""
        if self.had_key:
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.sub_key) as key:
                    for name, (val, val_type) in self.backup_values.items():
                        winreg.SetValueEx(key, name, 0, val_type, val)
            except OSError as exc:
                print(f"[UYARI] Registry kaydı geri yüklenirken hata: {exc}")
        else:
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, self.sub_key)
            except OSError:
                pass


def installer_check(installer_path: Path) -> None:
    """Kurulum dosyasını geçici klasöre kurar, exe'yi ve kaldırıcıyı test eder."""
    if not installer_path.exists():
        raise FileNotFoundError(f"Kurulum dosyası bulunamadı: {installer_path}")

    temp_install_dir = Path(tempfile.mkdtemp(prefix="pkm_test_install_"))
    log_path = temp_install_dir / "install_test.log"

    print(f"\n[Kurulum Doğrulama] Geçici dizine test kurulumu yapılıyor: {temp_install_dir}")

    with RegistrationGuard(APP_ID):
        try:
            # 1. Sessiz kurulum
            install_cmd = [
                str(installer_path),
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                "/CURRENTUSER",
                f"/DIR={temp_install_dir}",
                f"/LOG={log_path}",
            ]
            res = subprocess.run(install_cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Kurulum testi başarısız oldu (kod: {res.returncode}). Log: {log_path}")

            installed_exe = temp_install_dir / "KaynakYonetimPlatformu.exe"
            if not installed_exe.exists():
                raise FileNotFoundError(f"Kurulan exe bulunamadı: {installed_exe}")

            # 2. Kurulan exe'nin çalışmasını test et
            launch_check(installed_exe, seconds=5.0)

            # 3. Kaldırıcıyı test et (kaldırıcı da imzasız exe'dir!)
            uninstaller = temp_install_dir / "unins000.exe"
            if uninstaller.exists():
                print(f"  [Kaldırıcı Doğrulama] {uninstaller.name} çalıştırılıyor...")
                unins_cmd = [str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
                unins_res = subprocess.run(unins_cmd, capture_output=True, text=True)
                if unins_res.returncode != 0:
                    print(f"  [UYARI] Kaldırıcı çıkış kodu: {unins_res.returncode}")
                else:
                    print("  [Kaldırıcı Başarılı] Kaldırıcı sorunsuz çalıştı.")

            print("[Kurulum Doğrulama Başarılı] Kurulum dosyası ve kurulan exe doğrulandı.\n")
        finally:
            shutil.rmtree(temp_install_dir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python build_verify.py <exe_veya_setup_yolu>")
        sys.exit(1)

    target = Path(sys.argv[1]).resolve()
    if target.suffix.lower() == ".exe" and "setup" in target.name.lower():
        installer_check(target)
    else:
        launch_check(target)
