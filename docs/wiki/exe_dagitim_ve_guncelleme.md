# Windows Exe, Dağıtım ve Uygulama İçi Güncelleme Sistemi

**İlgili:** [[rules]] · [[mimari_kurallari]] · [[dizin_yapisi]] · [[qml_arayuz]]

Bu sayfa, uygulamanın kod imzalamasız (unsigned) olarak Windows 11 Akıllı Uygulama Denetimi (Smart App Control - SAC) ve SmartScreen engellerine takılmadan paketlenmesi, GitHub Actions ile sürüm etiketi (`vX.Y.Z`) üzerinden yayınlanması ve uygulama içi sessiz güncelleme mimarisini açıklar.

---

## 1. Kararlı Exe İlkesi (Deterministic Launcher)

Windows SAC, imzasız her yeni çalıştırılabilir dosyanın SHA-256 özetini Microsoft bulut itibar sistemine sorar. Her sürümde exe içeriği değişirse, kullanıcılar rastgele "Uygulama Denetimi ilkesi bu dosyayı engelledi" (WinError 4551 / 1260) hatasıyla karşılaşır.

**Çözüm:**
1. **Sabit Başlatıcı (`packaging/launcher.py`):** Yalnızca 3 satırdır ve `from main import main; main()` çağırır. İçeriği asla değiştirilmez; exe özetini belirleyen sabit bir kabuktur.
2. **Kodlar Exe Dışında:** PyInstaller `--debug=noarchive` bayrağı ile modüller `.pyc` olarak `_internal/` klasöründe tutulur. Sürüm yükseltmelerinde exe değişmez, yalnızca `.pyc` dosyaları güncellenir.
3. **Zaman Damgası Sabitleme:** `SOURCE_DATE_EPOCH=1700000000` ortam değişkeni PE zaman damgasını dondurur.
4. **Sabit PE Sürümü (`packaging/launcher_version_info.txt`):** Gezgin dosya özellikleri sabit `1.0.0.0` olarak kalır. Gerçek ürün sürümü `core/version.py`, kurulum sihirbazı ve uygulama arayüzünde görünür.
5. **Onay Kapısı (`packaging/launcher.sha256`):** Yerelde ve CI'da derlenen launcher özeti bu dosya ile karşılaştırılır; özet beklenmedik şekilde değişirse derleme ve yayın derhal durur (`sys.exit(1)`).

---

## 2. Kurulum Sihirbazı (Inno Setup 6)

`packaging/P011_KaynakYonetim.iss`:
- **Sabit AppId:** `{{7470CA3F-5001-4DFC-BFF7-5535C9C85DAD}}` (güncellemelerin mevcut kurulumun üstüne yazması için değiştirilmez).
- **Kullanıcı Yetkisi (`PrivilegesRequired=lowest`):** Kurulum `%LOCALAPPDATA%\Programs\KaynakYonetimPlatformu` altına yapılır. UAC şifresi sormaz, standart kullanıcı yetkisiyle sessiz güncellenebilir.
- **Sessiz Yeniden Başlatma (`Check: RelaunchAfterUpdate`):** Uygulama içi güncelleme `/SILENT` ile çalıştığında kurulum bitiminde uygulamayı kendiliğinden açar; test amaçlı `/VERYSILENT` kurulumlarında açmaz.
- **Çalışan Uygulamayı Kapatma (`CloseApplications=yes`):** Güncelleme sırasında dosya kilidi hatası oluşmaması için Inno Setup çalışan eski uygulamayı kapatır.

---

## 3. Sürüm Yayınlama Süreci

1. **Tek Sürüm Kaynağı:** `core/version.py` (`__version__ = "X.Y.Z"`, `RELEASE_REPO = "Yusufygc/CalismaKaynaklari_Yonetim_Platformu"`).
2. **Sürüm Aracı (`tools/release.py`):**
   ```powershell
   python tools/release.py 1.0.1
   git push origin main
   git push origin v1.0.1
   ```
   Çalışma ağacının temiz olduğunu denetler, `core/version.py` sürümünü yükseltir, `chore(release): vX.Y.Z` commit'i atar ve ek açıklamalı git etiketi (`vX.Y.Z`) oluşturur.
3. **GitHub Actions (`.github/workflows/release.yml`):**
   - `v*` etiketi push edildiğinde tetiklenir (`windows-latest`).
   - `tools/release.py --check-tag` ile etiket ve sürüm uyumunu doğrular.
   - Testleri (`pytest`) ve bağımlılık taramasını (`pip-audit`) koşar.
   - `python build_installer.py` ile uygulamayı derler, onay kapısını (`launcher.sha256`) denetler, Inno Setup kurulum dosyasını ve `.sha256` özetini üretir.
   - `gh release create` ile GitHub Releases'e yükler.

---

## 4. Uygulama İçi Güncelleme Mimarisi

- **Servis (`services/update_service.py`):**
  - GitHub Releases API (`releases/latest`) üzerinden yeni sürüm denetimi. Ön sürümleri ve taslakları yok sayar, sayısal semver kıyaslaması yapar (`1.10.0 > 1.9.0`).
  - Sıkı güvenlik kontrolleri: İndirme URL'si yalnızca `https://github.com/{repo}/releases/download/...` kabul edilir. Kurulum dosya adı regex'e uymalıdır (`KaynakYonetimPlatformu-Setup-X.Y.Z.exe`). Maksimum boyut sınırı 400 MB'tır.
  - **Zorunlu SHA-256:** Asset `digest` veya `.sha256` dosyasından doğrulanır; özet yoksa veya uyuşmazsa dosya silinir ve güncelleme reddedilir.
  - **Bağımsız Süreç:** `/SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /LOG=...` ile başlatılır.
- **Windows SAC Otomatik Yeniden Deneme (Emniyet Ağı):**
  - Windows Akıllı Uygulama Denetimi kurulum dosyasını ilk anda engellerse (`WinError 4551 / 1260`), `UpdateBridge` 15 saniyede bir en çok 40 kez (10 dakika) kurulumu başlatmayı dener.
  - Engel kalkınca kurulum başlar ve uygulama kapanır.
  - Kullanıcı vazgeçerse veya süre dolarsa dosya Gezgin'de seçili gösterilir (`explorer.exe /select,...`).
- **Arayüz (`qml/dialogs/UpdateDialog.qml` & `qml/components/UpdateSettingsPanel.qml`):**
  - Minimalist tasarım dili (Theme token'ları).
  - İlerleme çubuğu, sürüm notları kutusu, "Şimdi Güncelle", "Bu Sürümü Atla", "Daha Sonra".
  - Ayarlar ekranında açılışta otomatik denetleme tercihi ve "Şimdi Denetle" butonu.
  - Açılışta 3 saniye sonra arka planda sessiz denetim (`QTimer.singleShot(3000, bridge.update.startupCheck)`). `PKM_NO_UPDATE_CHECK=1` ortam değişkeniyle testlerde devre dışı bırakılabilir.

---

## 5. Doğrulama Komutları

```powershell
# Sadece exe derleme ve onay kapısı denetimi
python build_exe.py

# Tek komutla exe + Inno Setup + yerel doğrulama + .sha256 üretimi
python build_installer.py

# Exe özetini bilerek güncellemek için (yalnızca yerelde test edildikten sonra)
python build_installer.py --update-launcher-hash
```
