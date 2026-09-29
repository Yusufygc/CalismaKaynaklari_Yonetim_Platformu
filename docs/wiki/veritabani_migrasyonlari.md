# Veritabanı Migrasyonları (Alembic)

Şema değişiklikleri artık [Alembic](https://alembic.sqlalchemy.org/) ile versiyonlanır. Eskiden `utils/db_utils.py` içinde `Base.metadata.create_all()` + elle yazılmış `_LIGHTWEIGHT_MIGRATIONS` listesi (tek satır `ALTER TABLE`) kullanılıyordu; bu mekanizma kolon silme/tip değiştirme gibi senaryoları desteklemiyordu ve yeni her değişiklik için elle liste güncellemesi gerektiriyordu.

## Dosya Yerleşimi

- `alembic.ini` — Alembic konfigürasyonu (2026-09-28: `pkm_app/` klasörü kaldırıldı, kök dizine taşındı).
- `migrations/env.py` — modelleri import edip `Base.metadata`'yı `target_metadata` yapar, DB URL'ini `core.config.settings.DATABASE_URL`'den okur (alembic.ini'deki placeholder ezilir).
- `migrations/versions/` — revizyon dosyaları. İlk revizyon (`..._baseline.py`) mevcut 7 tabloyu (`categories`, `tags`, `resources`, `resource_tags_link`, `highlights`, `vocabulary`, `ideas`) `alembic revision --autogenerate` ile üretildi. İkinci revizyon (`..._ideas_tablosunu_kaldir.py`), Fikirler modülü kaldırılırken `ideas` tablosunu drop eder. Üçüncü revizyon (`ff016ad9bf6e_kaynak_filtre_kolonlarina_index_ekle.py`, 2026-07-03), N+1 sorgu denetimi sonrası `resources.status/category_id/is_favorite/is_pinned/url` kolonlarına index ekler (`query_filtered`'ın tam bu kolonlarda filtrelediği tespit edildi, önceden sadece PK indeksliydi). Dördüncü revizyon (`6e58af46d8a6_progress_kolonunu_kaldir.py`, 2026-07-06), İlerleme (%) özelliğinin komple kaldırılmasıyla artık kullanılmayan `resources.progress` kolonunu düşürür — SQLite `DROP COLUMN`'u desteklemediği için `op.batch_alter_table()` kullanılır (bu repo'daki ilk batch-mode migration). Beşinci revizyon (`73989d002a5c_resources_full_text_ekle.py`, 2026-07-06), okuyucu sayfası için `resources.full_text` (Text, nullable) kolonunu ekler — sadece `ADD COLUMN` olduğu için batch mode gerekmez, doğrudan `op.add_column`.

## `init_db()` Akışı (`utils/db_utils.py`)

Üç senaryo ayırt edilir (`inspect(engine).get_table_names()` ile):

1. **Sıfırdan kurulum** (hiç tablo yok): `alembic upgrade head` migration zincirini baştan çalıştırır, tüm tabloları oluşturur.
2. **Alembic-öncesi (legacy) veritabanı** (tablolar var ama `alembic_version` yok — örn. bu değişiklikten önce oluşturulmuş bir kullanıcı DB'si): şemaya dokunmadan `alembic stamp head` ile mevcut durum "head" olarak işaretlenir. Kullanıcı verisi korunur, `CREATE TABLE` çakışması olmaz.
3. **Zaten Alembic ile yönetilen DB**: sadece bekleyen migration'lar (varsa) uygulanır.

`_apply_lightweight_migrations()` (eski mekanizma) hâlâ `init_db()`'nin başında çalışır — çok eski bir DB dosyasında `is_favorite` kolonu bile yoksa önce onu ekler, sonra Alembic akışı devreye girer. Yeni şema değişiklikleri için bu listeye eklenme yapılmaz; bunun yerine yeni bir Alembic revizyonu oluşturulur.

## Yeni Migration Ekleme

```bash
alembic revision --autogenerate -m "kisa_aciklama"
# uretilen dosyayi migrations/versions/ altinda incele, gerekirse elle duzelt
```

`env.py` zaten `Base.metadata`'yı okuduğu için modelde yapılan değişiklik otomatik algılanır. Üretilen dosya mutlaka gözden geçirilmeli (autogenerate her zaman doğru `downgrade()` üretmeyebilir, index/constraint isimlendirmesi bazen elle düzeltme ister).

**Gerçek DB'ye dokunmadan autogenerate:** CLI üzerinden `alembic revision --autogenerate` çalıştırırken de aşağıdaki ⚠️ tuzak geçerlidir. Programatik `alembic_command.upgrade(...)` çağrılarında `monkeypatch.setattr(db_utils.settings, "DATABASE_URL", ...)` kullanılırken, CLI'dan çalıştırırken en basit yöntem `DATABASE_URL` ortam değişkenini komuttan önce **geçici bir kopya DB'ye** işaret edecek şekilde export etmektir — `core.config.Settings` pydantic `BaseSettings` olduğu için süreç başlarken ortam değişkenini otomatik okur, `.env` dosyasını ezer:
```bash
export DATABASE_URL="sqlite:///</path/to/scratch/gecici.db>"
alembic upgrade head            # eski semayi gecici DB'de olustur
alembic revision --autogenerate -m "..."
alembic upgrade head && alembic downgrade -1   # olustur/geri al dongusunu dogrula
```
Gerçek DB'ye asla dokunulmaz; migration dosyası incelendikten sonra gerçek DB'ye uygulanması bir sonraki normal `init_db()` başlangıç akışına bırakılır.

## Doğrulama Notu

Bu geçiş, gerçek kullanıcı veritabanının (`%APPDATA%/PKM/pkm_app.db`) bir **kopyası** üzerinde test edildi: legacy senaryoda tüm satırlar (resources, categories, tags, ideas) değişmeden korundu, `alembic_version` doğru eklendi, ikinci `init_db()` çağrısı idempotent çalıştı. Orijinal dosyaya dokunulmadı (MD5 doğrulandı).

## ⚠️ Tuzak: `env.py` her zaman `settings.DATABASE_URL`'i kullanır

`migrations/env.py:36` — `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)` — bu satır, `alembic_command.upgrade(cfg, ...)` çağrısına **hangi `AlembicConfig` nesnesi verilirse verilsin**, env.py import edildiği an URL'i `core.config.settings.DATABASE_URL` (gerçek prod DB yolu) ile ezer. Bir migration'ı bir **kopya** DB üzerinde test etmek için `cfg.set_main_option("sqlalchemy.url", ...)` YETMEZ — `core.config.settings.DATABASE_URL`'in kendisini (örn. `monkeypatch.setattr(db_utils.settings, "DATABASE_URL", kopya_url)` ile, bkz. `tests/test_repositories/test_db_utils.py`) geçici olarak değiştirmek gerekir. Aksi halde migration sessizce gerçek veritabanına uygulanır.

## Migration Öncesi Otomatik Yedek (2026-09-30)

`utils/db_utils.py::init_db` bekleyen migration varsa (ya da Alembic-öncesi `legacy` DB ise) upgrade/stamp'ten **önce** `pkm_app.db.bak-<YYYYmmdd-HHMMSS>-<mevcut revision>` dosyası oluşturur (SQLite `backup` API'si — WAL içeriğini de kapsar). Son 3 yedek tutulur (`_prune_backups`). Yeni kurulumda ve güncel (head) DB'de yedek alınmaz. Yedekten dönmek için uygulamayı kapatıp `.bak-...` dosyasını `pkm_app.db` adıyla geri kopyalamak yeterlidir. Testler: `tests/test_repositories/test_db_backup.py`.
