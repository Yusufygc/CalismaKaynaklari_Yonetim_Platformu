# Wiki İçerik Haritası — PKM / Kaynak Yönetim Platformu

**Stack:** PySide6 QML · SQLAlchemy 2.0 · SQLite · Alembic  
**Ortam:** proje kökündeki `.venv` (Python 3.10)

---

## Kurallar ve Mimari

| Sayfa | Özet |
|-------|------|
| [[rules]] | Projenin anayasası: yazılım prensipleri, katman/DI kuralları, wiki ve commit disiplini, izinli log işlem tipleri |
| [[mimari_kurallari]] | SOLID, Clean Code, DRY, merkezi varlık yönetimi, katman kuralları |
| [[dizin_yapisi]] | Proje kök dizini, her modülün sorumluluğu, katman tablosu |

## Veritabanı

| Sayfa | Özet |
|-------|------|
| [[veritabani_semasi]] | Tüm tablolar (categories, tags, resources, highlights, vocabulary ve pdfkit tabloları: belgeler, alıntı/not/kelime, okuma durumu, vault citekey, tam metin dizini), alan tanımları |
| [[veritabani_migrasyonlari]] | Alembic'e geçiş: env.py yapılandırması, init_db() fresh/legacy/managed akışı, yeni migration ekleme |

## Servisler ve İş Mantığı

| Sayfa | Özet |
|-------|------|
| [[core_servisler]] | Repository/Service/Controller katmanları, ResourceService.update_resource, TagService CRUD, URL regex, custom exceptions |

## PDF Modülü

| Sayfa | Özet |
|-------|------|
| [[pdfkit]] | Bağımsız PDF paketi (Faz 0–8 tamam): içerik adresli belge deposu, alıntı çapası ve artımlı modeller, okuma durumu, Obsidian vault (belge/dizin/kelime defteri/matris notları, `pkm://` derin bağlantı), PDF içi tam metin araması (FTS5), künye doldurma, literatür matrisi, daraltma (eski yol temizliği, `repair_paths`) |

## Arayüz (UI/UX)

| Sayfa | Özet |
|-------|------|
| [[qml_arayuz]] | QML/QtQuick mimarisi: Notion/Linear tasarım dili, Slide-over Inspector, QmlBridge, ResourceListModel |

## Altyapı

| Sayfa | Özet |
|-------|------|
| [[event_bus]] | Singleton+Observer event sistemi, sinyaller, emit/connect kuralları |

## Meta

| Sayfa | Özet |
|-------|------|
| [[log]] | Kronolojik değişiklik kayıt defteri |

---

## Operasyon Komutları (Anayasa)

| Komut | Ne yapar |
|-------|----------|
| `[INGEST]` | Yeni kaynak al → wiki sayfası oluştur → `index.md` + `log.md` güncelle |
| `[QUERY]` | `index.md` → ilgili sayfa → wiki bilgisiyle cevap ver |
| `[LINT]` | Çelişki, orphan sayfa, kırık link tara → rapor sun → onay sonrası düzelt |

**Kural:** Her sohbet başında `docs/wiki/index.md` okunur. Sıfırdan keşif yapılmaz; biriken bilgi kullanılır.
