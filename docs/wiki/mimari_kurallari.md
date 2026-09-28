# Mimari ve Kodlama Kuralları

**Kaynak (Raw Source):** `rules.md` (kök dizin)

## Yazılım Prensipleri
- **SOLID:** Tek sorumluluk, genişlemeye açık/değişime kapalı, Dependency Inversion için ABC kullan.
- **Clean Code:** İsimler self-documenting (`extract_metadata_from_url()` > `process_data()`). Yorumlar sadece "Neden?" için.
- **DRY:** Ortak mantık `utils/` veya `helpers/` altına taşınır.
- **Teknik Borç Yasağı:** "Şimdilik çalışsın" (hack) yaklaşımı yasaktır.

## Merkezi Varlık Yönetimi
| Kaynak | Dosya |
|--------|-------|
| Stringler | `core/constants/strings.py` |
| Renkler | `core/constants/colors.py` |
| Fontlar | `core/constants/fonts.py` |
| İkonlar | `core/constants/icons.py` + `assets/icons/` (SVG) |

## Stil Yönetimi (QSS)
- `setStyleSheet` inline kullanımı YASAKTIR.
- Stiller `assets/styles/` altında modüler `.qss` dosyalarında tutulur.
- Renkler `colors.py` üzerinden dinamik formatlanarak QSS'e enjekte edilir.

## Mimari Desenler
- **MVC/MVP:** UI veritabanını doğrudan çağıramaz; her zaman Controller/Service üzerinden.
- **Repository Pattern:** DB sorguları `repositories/` içinde izole edilir.
- **Dependency Injection:** Session ve bağımlılıklar `__init__` üzerinden dışarıdan alınır.
- **Event-Driven UI:** UI güncellemeleri için PySide6 `Signal/Slot` kullanılır → bkz. [[event_bus]].

## UI Katmanları (Compose → Workspace → Flow)
- **Window (compose):** `MainWindow` yalnızca alt parçaları üretir ve `QSplitter` ile yerleştirir. İş mantığı yok.
- **Workspace (page dispatcher):** `ContentWorkspace` çoklu sayfa + filter dispatcher (sözlük tabanlı, `if/elif` zinciri yok). `apply_filter`/`refresh` public API.
- **Flow (coordinator):** `ResourceFlow` UI bileşenleri ile `MainController` arasındaki yaşam döngüsü sinyallerini bağlar — widget değil, koordinatör.
- **Controller (facade + delegasyon, 2026-09-28):** `MainController` artik is mantigi tasimiyor — 25 metodluk god-object'ti (SRP ihlali), alan bazli 5 alt-controller'a bolundu: `ResourceController`, `CategoryController`, `TagController`, `HighlightController`, `VocabularyController` (hepsi `ui/controllers/`). Her biri kendi Service'ini enjekte eder + UI sinirindaki `try/except → log + event_bus.error_occurred.emit` desenini tasir. `MainController` sadece bunlari `__init__`'te kurup ayni public metod imzalariyla delege eden ince bir facade — `main.py`, `ResourceFlow`, `ContentWorkspace`, `SettingsView`, `KnowledgePoolView` gibi tuketiciler tek bir `controller` nesnesi enjekte etmeye devam eder, hicbiri degismedi (public API birebir korundu, testler degismeden gecti).
- **Component sayfaları:** `DetailView` gibi stack koordinatörlerinde her sayfa bağımsız `QWidget` bileşeni olmalıdır (`EmptyDetail`, `ResourceDetailPanel`, `ResourceForm`). View koordinatörü alt sinyalleri dışarıya **aynı isimle relay** eder; dış API kırılmaz.

## Konfigürasyon, Hata, Log
- **Config:** `core/config.py` (Pydantic BaseSettings veya `os.environ`)
- **Exceptions:** `core/exceptions.py` özel sınıflar → bkz. [[core_servisler]]
- **Logger:** `core/logger.py` — konsol + dosya (`app.log`), `print()` yasaktır.

## Yol Çözümleme (Exe Uyumlu)
- **Tek nokta:** `core/paths.py`. Doğrudan `__file__` + relative traversal **yasak**.
- `resource_path(*parts)` → salt-okunur paket içi kaynaklar (QSS, ikon). Frozen exe'de `sys._MEIPASS`, dev'de `pkm_app/` kökü.
- `user_data_dir()` → yazılabilir kullanıcı verisi (SQLite, `app.log`). Windows `%APPDATA%/PKM`, macOS `~/Library/Application Support/PKM`, Linux `$XDG_DATA_HOME/PKM`.
- PyInstaller build örneği: `pyinstaller --onefile --windowed --add-data "pkm_app/assets;pkm_app/assets" pkm_app/main.py`.

## İlgili Sayfalar
[[dizin_yapisi]] · [[core_servisler]] · [[event_bus]] · [[tema_yonetimi]]
