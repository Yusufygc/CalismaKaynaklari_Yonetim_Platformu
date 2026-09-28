# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- **Conda env:** `C:\Users\ysfygc\anaconda3\envs\KaynakYonetim`
- **Activate:** `conda activate KaynakYonetim`
- **Run app:** `python main.py`
- **Install deps:** `pip install -r requirements.txt`
- **Run tests:** `pytest tests/`
- **Single test:** `pytest tests/test_services/test_resource_service.py::TestClassName::test_method`

## Wiki (Read First)

Before any code change, read `docs/wiki/index.md`. It maps every architectural decision. Follow links to relevant pages rather than re-deriving from scratch.

Operasyon komutları: `[INGEST]` yeni kaynak al → wiki güncelle, `[QUERY]` wiki üzerinden cevapla, `[LINT]` wiki sağlık kontrolü.

## Architecture

Three-layer separation — UI never touches the database directly:

```
QML UI (qml/ views, components, theme)
  └── QmlBridge & Controllers (controllers/ dir)
          └── Services (business logic, validation, commit/rollback)
                  └── Repositories (SQLAlchemy queries only, no business logic)
                          └── Models (SQLAlchemy declarative, models/ dir)
```

**QML UI & Theme** (`qml/`) — Notion / Linear / Craft minimalist tasarım dili. Singleton `Theme.qml` tüm renk, tipografi, kenarlık ve animasyon token'larını reaktif olarak yönetir.

**Event Bus** (`core/events.py`) — Singleton `_EventBus(QObject)`. Controller'lar ve servisler arası durum değişimleri `event_bus.signal.emit()` / `.connect()` üzerinden akar.

**Session ownership:** `commit()` and `rollback()` belong in the Service layer, never in Repositories.

## Hard Rules

**Code principles:**
- **SOLID:** Every class has single responsibility. Open/Closed: extend, don't modify. Use ABCs for Dependency Inversion.
- **DRY:** No repeated logic. Common functions go to `utils/` or `helpers/`.
- **No hacks:** "Works for now" shortcuts are forbidden. Every module must be testable and isolated when written.

**Styling:**
- All design tokens live in `qml/theme/Theme.qml` (colors, spacing, radius, typography).
- No hardcoded ad-hoc color codes in QML component bodies — reference `Theme.*`.

**Assets:**
- Standard icons: `qtawesome` via `image://icon/<name>/<hex>` (`IconImageProvider`). Custom SVG icons in `assets/icons/`.

**Error & observability:**
- No `print()`. Use `core/logger.py` (logs to console + `app.log`).
- Raise project-specific exceptions from `core/exceptions.py` (`InvalidURLError`, `ResourceNotFoundError`, `ValidationError`, `DuplicateRecordError`) — not bare `Exception`.

**Config & DI:**
- Config via `core/config.py` (Pydantic `BaseSettings` or `os.environ`). No hardcoded paths.
- Session and dependencies passed through `__init__`, not created inside classes.

## Wiki Güncellemesi

Her kod değişikliği, yeni modül, kütüphane ekleme veya mimari karar sonrasında:
1. İlgili `docs/wiki/*.md` sayfasını güncelle.
2. `docs/wiki/log.md` dosyasının **en üstüne** giriş ekle: `## [YYYY-AA-GG] [İŞLEM_TİPİ] | Kısa açıklama`
3. Yeni sayfa açıldıysa `docs/wiki/index.md`'ye de ekle.

## Commit Kuralları

- Commit mesajları **Türkçe** yazılır. Türkçe karakterlere dikkat et (ş, ğ, ü, ö, ı, ç).
- Başlık ≤ 50 karakter, açıklayıcı ve işlemin "neden" yapıldığını anlatan gövde.
- Commit mesajlarında "Claude Code" veya herhangi bir AI aracı referansı **verilmez**.

## Key Files

| Purpose | Path |
|---------|------|
| Entry point | `main.py` |
| QML Root Window | `qml/main.qml` |
| Theme Singleton | `qml/theme/Theme.qml` |
| Python-QML Bridge | `ui_qml/bridge.py` |
| Virtualized List Model | `ui_qml/models/resource_list_model.py` |
| Main Controller Facade | `controllers/main_controller.py` |
| Core business logic | `services/resource_service.py` |
| Background workers | `workers/` (`scrape_worker.py`, `extract_worker.py`) |

## Database

SQLite + SQLAlchemy 2.0 declarative. Main tables: `resources` (has `extra_metadata JSON` for type-specific data), `categories`, `tags`, `resource_tags_link` (N:N), `highlights`, `vocabulary`. All datetimes UTC via `default=func.now()`.
