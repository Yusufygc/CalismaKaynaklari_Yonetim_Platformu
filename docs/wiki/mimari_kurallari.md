# Mimari ve Kodlama Kuralları

**Kaynak:** [[rules]] (`docs/wiki/rules.md`)

## Yazılım Prensipleri
- **SOLID:** Tek sorumluluk, genişlemeye açık/değişime kapalı, Dependency Inversion için ABC kullan.
- **Clean Code:** İsimler self-documenting (`extract_metadata_from_url()` > `process_data()`). Yorumlar sadece "Neden?" için.
- **DRY:** Ortak mantık `utils/` veya `helpers/` altına taşınır.
- **Teknik Borç Yasağı:** "Şimdilik çalışsın" (hack) yaklaşımı yasaktır.

## Merkezi Varlık Yönetimi
| Kaynak | Dosya |
|--------|-------|
| Stringler | `core/constants/strings.py` (`AppStrings`) |
| Tasarım Token'ları | `qml/theme/Theme.qml` (renkler, fontlar, radius, gölgeler) |
| İkonlar | `ui_qml/image_provider.py` (`image://icon/`) + `assets/icons/` (SVG) |

## Stil Yönetimi (QML Declarative Theme)
- Bileşen içi inline hardcoded renk kullanımı YASAKTIR.
- Tüm stil ve görsel token'lar `qml/theme/Theme.qml` singleton'ı üzerinden yönetilir.
- Notion / Linear minimalist tasarım dili; reaktif `isDark` temalandırması kullanılır.

## Mimari Desenler
- **MVC/MVP:** UI veritabanını doğrudan çağıramaz; her zaman Controller/Service üzerinden.
- **Repository Pattern:** DB sorguları `repositories/` içinde izole edilir. `commit()` ve `rollback()` sadece `services/` katmanındadır.
- **Dependency Injection:** Bağımlılıklar `__init__` üzerinden dışarıdan alınır; bileşenler mock'lanabilir olmalıdır.
- **Event-Driven UI:** UI güncellemeleri için PySide6 `Signal/Slot` ve `event_bus` kullanılır → bkz. [[event_bus]].

## Katman Hiyerarşisi
- `qml/` (Views, Components, Theme) -> `ui_qml/` (Bridge, List Models) -> `controllers/` (MainController Facade & Sub-controllers) -> `services/` (Business Logic & Transactions) -> `repositories/` (SQLAlchemy Queries) -> `models/` (Declarative Entities)
- `workers/`: Arka plan iş parçacıkları (`scrape_worker.py`, `extract_worker.py`) `QThreadPool` ile yönetilir.
- `core/`: En alt altyapı katmanıdır (logger, paths, config, exceptions, net_utils, events). Üst katmanlara bağımlılığı kesinlikle yoktur.

## Controller Mimarisi
- `MainController` (`controllers/main_controller.py`): Tek bir DI noktası sağlayan ince bir facade'dir. Alan bazlı 5 alt-controller'a delege eder: `ResourceController`, `CategoryController`, `TagController`, `HighlightController`, `VocabularyController` (hepsi `controllers/` altında).

## Konfigürasyon, Hata, Log
- **Config:** `core/config.py` (Pydantic BaseSettings veya `os.environ`)
- **Exceptions:** `core/exceptions.py` özel sınıflar → bkz. [[core_servisler]]
- **Logger:** `core/logger.py` — konsol + dosya (`app.log`), `print()` yasaktır.

## Yol Çözümleme (Exe Uyumlu)
- **Tek nokta:** `core/paths.py`. Doğrudan `__file__` + relative traversal **yasak**.
- `resource_path(*parts)` → salt-okunur paket içi kaynaklar (QSS, ikon). Frozen exe'de `sys._MEIPASS`, dev'de proje kökü (2026-09-28: `pkm_app/` klasörü kaldırıldı, kod doğrudan kökte).
- `user_data_dir()` → yazılabilir kullanıcı verisi (SQLite, `app.log`). Windows `%APPDATA%/PKM`, macOS `~/Library/Application Support/PKM`, Linux `$XDG_DATA_HOME/PKM`.
- PyInstaller build örneği: `pyinstaller --onefile --windowed --add-data "assets;assets" main.py`.

## İlgili Sayfalar
[[dizin_yapisi]] · [[core_servisler]] · [[event_bus]] · [[qml_arayuz]]
