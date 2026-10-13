# Veritabanı Şeması

**Kaynak (Raw Source):** `veritabani.md` (kök dizin)

## Teknoloji Yığını
- **DB:** SQLite
- **ORM:** SQLAlchemy 2.0 (declarative mapping)
- **Tarihler:** UTC `datetime`, `default=func.now()`

## Tablolar

### `categories`
| Alan | Tip | Not |
|------|-----|-----|
| id | Integer PK | |
| name | String | Unique, Required |
| color_hex | String | Örn: `#FF0000` |
| icon | String | qtawesome kodu veya emoji |

### `tags`
| Alan | Tip | Not |
|------|-----|-----|
| id | Integer PK | |
| name | String | Unique, Required, küçük harf+boşluksuz |

### `resources` (Ana Tablo)
| Alan | Tip | Not |
|------|-----|-----|
| id | Integer PK | |
| title | String | Required |
| url | String | Nullable, **indexed** (2026-07-03) |
| category_id | Integer FK | `categories.id`, **indexed** (2026-07-03) |
| status | Enum | `INBOX` / `PLANNED` / `IN_PROGRESS` / `COMPLETED`, **indexed** (2026-07-03) |
| priority | Integer | 1-2-3, default 2 |
| is_pinned | Boolean | default False — listede üste sabitler, **indexed** (2026-07-03) |
| is_favorite | Boolean | default False — "Favoriler" koleksiyonu, **indexed** (2026-07-03) |
| content | Text | Markdown formatında notlar |
| full_text | Text | Nullable — okuyucu sayfasında gösterilen ham kaynak metni: URL'den `trafilatura` ile çıkarılan makale gövdesi (2026-07-06, migration `73989d002a5c`). `content`'ten ayrı — biri kullanıcının kendi notu, diğeri kaynağın orijinal metni. **`deferred`** (2026-09-30): liste/filtre sorguları tam metni yüklemez, yalnızca özniteliğe erişilince (okuyucu, `ResourceSerializer`) lazy yüklenir |
| reading_minutes | Integer | Required, varsayılan 0 — tahmini okuma süresi (dk). `full_text` (yoksa `content`) değişince `ResourceService` `utils/reading_time.estimate_reading_minutes` ile yeniden hesaplar; migration `e1f4a9c07b2d` mevcut kayıtları geri doldurdu. Kartlar ve okuyucu bunu okur (2026-09-30) |
| extra_metadata | JSON | **Esnek alan** — tip-özel veriler (süre, yıldız, yazar…) |
| created_at | DateTime | default now |
| updated_at | DateTime | default now, onupdate now |

**Kategori silme:** `resources.category_id` FK davranışı `ON DELETE SET NULL` olarak kalır. ORM tarafında category->resources ilişkisinde `delete-orphan` yoktur; kategori silinince kaynak kaydı korunur.

**İndexler (migration `ff016ad9bf6e`):** `query_filtered` (bkz. [[core_servisler]]) tam olarak `status`/`category_id`/`is_favorite`/`is_pinned`/`url` kolonlarında filtreliyor ve sıralıyor; önceden sadece PK indeksliydi (full-table-scan riski). Bkz. [[veritabani_migrasyonlari]].

**`progress` kolonu kaldırıldı (migration `6e58af46d8a6`, 2026-07-06):** İlerleme yüzdesi özelliği UI'dan tamamen kaldırıldı; `status`, artık `progress`'ten otomatik türetilmiyor — tamamen manuel (`Durum` combo'su üzerinden).

### `resource_tags_link` (N:N)
| Alan | Tip |
|------|-----|
| resource_id | FK → resources.id |
| tag_id | FK → tags.id |

### `highlights` (Alıntılar — 2026-07-06'da aktif edildi)
| Alan | Tip | Not |
|------|-----|-----|
| id | Integer PK | |
| resource_id | FK | `resources.id`, `ondelete=CASCADE` |
| content | Text | Required |
| page_number | Integer | Nullable — HTML-makale highlight'larında hep null; native PDF highlight'larında (2026-09-29) sayfa indeksi dolu |
| color | String | Nullable — kullanıcı seçim toolbar'ında `Theme.highlightPalette`/`Colors.HIGHLIGHT_PALETTE`'ten renk seçer; boşsa (legacy kayıt) tema varsayılanı kullanılır. PDF'te reader-içi renk degistirme de var (`updateHighlightColor`) |
| start_index | Integer | Nullable (2026-09-29) — sadece PDF highlight'larında dolu. `QPdfDocument.getSelectionAtIndex(page, start_index, length)` ile piksel/zoom'dan bağımsız yeniden çizilir |
| length | Integer | Nullable (2026-09-29) — `endIndex - startIndex` (dikkat: +1 DEĞİL, canlı testte doğrulandı) |
| comment | Text | Nullable (2026-09-29) — kullanıcının alıntıya eklediği serbest yorum (Alembic `8b3f1c2d9a47`). Anlam etiketi (Önemli/Bulgu/Yöntem/…) DB'de tutulmaz, `color`'dan türetilir (`core/constants/highlight_labels.py`) |
| created_at | DateTime | |

Repo/servis: `repositories/highlight_repo.py::HighlightRepository`, `services/highlight_service.py::HighlightService`. HTML okuyucusunda metin seçilip renk paletinden birine tıklanarak oluşturulur, silinebilir. Native PDF okuyucusunda (`PdfReaderView`, bkz. [[qml_arayuz]]) aynı highlight tablosu kullanılır ama oluşturma `bridge.annotations.addPdfHighlight` (page-point koordinatlarından `start_index`/`length` hesaplar) üzerinden, düzenleme (`updateHighlightColor`) + silme reader içinden yapılabilir — manuel ekleme formu hiçbir zaman olmadı.

### `vocabulary` (Kelime Dağarcığı — 2026-07-06'da aktif edildi)
| Alan | Tip | Not |
|------|-----|-----|
| id | Integer PK | |
| resource_id | FK | `resources.id`, `ondelete=CASCADE` |
| word | String | Required |
| translation | String | Required |
| context_sentence | Text | Nullable — bu turda doldurulmuyor (secili kelime + ceviri yeterli) |
| mastery_level | Integer | 0–5, default 0 — bu turda UI'da yok, gelecekteki spaced-repetition ozelligi icin ayrilmis alan |
| created_at | DateTime | |

Repo/servis: `repositories/vocabulary_repo.py::VocabularyRepository`, `services/vocabulary_service.py::VocabularyService`. Okuyucu sayfasında kelime seçilip "Kelime olarak kaydet" → ceviri icin inline popover ile olusturulur.

### `pdf_notes` (KALDIRILDI — pdfkit Faz 8, migration `c9f4e2b7a815`, 2026-10-13)
Eski tablo (`id, resource_id, page, x, y, note_text, created_at`) artık yazılmıyor; sayfa notları `pdf_page_notes` tablosundadır. Migration tabloyu **yalnız boşsa** siler; içinde taşınmamış satır varsa tablo korunur ve `LegacyAnnotationImporter` son satırı taşıyınca tabloyu kendisi kaldırır (kullanıcı verisi hiçbir koşulda silinmez). `PdfNote` ORM modeli, `PdfNoteRepository`, `PdfNoteService` ve `PdfNoteController` silindi. Bkz. [[pdfkit]] 'Daraltma (Faz 8)'.

### `saved_searches` (Makale Market Kayıtlı Arama — 2026-09-30'da eklendi, migration `c4d9a6b1e2f3`)
| Alan | Tip | Not |
|------|-----|-----|
| id | Integer PK | |
| topic | Text | Required (yazar aramasında boş olabilir) |
| filters | JSON | `yearFrom/yearTo/openAccess/workType/language/authorId/authorName` (yalnızca dolu olanlar) |
| tag_name | String(100) | Opsiyonel koleksiyon etiketi: bu aramadan kaydedilen makalelere eklenir |
| seen_ids | JSON | Kullanıcının gördüğü OpenAlex kimlikleri (en fazla 200, yenisi başta) |
| new_count | Integer | Son kontrolde `seen_ids` dışında kalan yeni yayın sayısı |
| last_checked_at | DateTime | Nullable — kontrol edilmemişse ya da ağ hatasıyla kontrol başarısızsa bir sonraki açılışta yeniden denenir |
| created_at | DateTime | |

Repo/servis/controller: `repositories/saved_search_repo.py`, `services/saved_search_service.py` (aynı konu+filtre tekrar kaydedilemez → `DuplicateRecordError`), `controllers/saved_search_controller.py`. Kaynaklarla ilişkisi yoktur (bağımsız tablo).

### `pdf_documents` / `pdf_resource_documents` (pdfkit belge deposu — 2026-10-12, migration `b3a91c5d7e20`)
Modeller `pdfkit/infra/orm.py` (ortak `Base`). `pdf_documents`: id, `sha256` (benzersiz), `rel_path` (depo köküne göre `store/ab/<sha>/<ad>.pdf`), `byte_size`, `page_count`, `has_text_layer`, `pdf_title`, `pdf_author`, `doi` (indeksli), `source` (`local`/`web`), `original_filename`, `imported_at`. `pdf_resource_documents`: `resource_id` (PK, FK → resources, CASCADE) → `document_id` (FK → pdf_documents, RESTRICT, indeksli); aynı PDF birden çok kaynakta olabilir, hiçbir kaynağa bağlı olmayan belge çöp toplamayla karantinaya alınır. Bkz. [[pdfkit]].

### `pdf_vault_notes` (pdfkit vault citekey — 2026-10-13, migration `a5d1e7c3b920`)
`PdfVaultNoteRow`: `document_id` (PK, FK → pdf_documents, CASCADE), `citekey` (benzersiz, ≤80; `[a-z0-9]`), `created_at`. Citekey ilk atamada yazılır ve değişmez; not yolu `Papers/<citekey>.md`. Servis `pdfkit/app/vault.py::CitekeyService`; bkz. [[pdfkit]] 'Obsidian vault: not modeli (Faz 5a)'.

### `pdf_text_index` / `pdf_page_fts` (pdfkit tam metin dizini — 2026-10-13, migration `b7e3c5a91d04`)
`PdfTextIndexRow`: `document_id` (PK, FK → pdf_documents, CASCADE), `status` (`indexing|ok|no_text|failed`), `page_count`, `version`, `indexed_at`. `pdf_page_fts`: FTS5 sanal tablosu (`folded` dizinli, `original` dizinsiz; `rowid = belge × 10000 + sayfa`); ORM metadata'sında yoktur (Alembic `include_object` ile karşılaştırma dışı). Yalnız `ok` belgeler aranır. Ayrıntı: [[pdfkit]] 'Kitaplık araması: tam metin dizini (Faz 6a)'.

### `pdf_reading_state` (pdfkit okuma durumu — 2026-10-13, migration `f2c8d4a61b93`)
Modeller `pdfkit/infra/orm.py::PdfReadingStateRow`. Birincil anahtar `document_id` (FK → pdf_documents, CASCADE). `last_page`, `loc_x`, `loc_y` (görünümün üstündeki sayfa ve sayfa içi konum), `zoom`, `max_page` (en uzak görülen sayfa; kart ilerlemesi), `total_seconds` (aktif okuma süresi), `updated_at`. Servis `pdfkit/app/reading.py::ReadingService`; bkz. [[pdfkit]] 'Okuma durumu (Faz 4a)'.

### `pdf_annotations` / `pdf_page_notes` / `pdf_terms` (pdfkit alıntı alanı — 2026-10-12, migration `d7e3b1a94c52`)
Modeller `pdfkit/infra/orm.py`. Ortak: `uid` (ULID, benzersiz), `document_id` (FK → pdf_documents, CASCADE), `legacy_id` (eski tablodaki id; benzersiz, geçici köprü için). `pdf_annotations`: `label_key`, `color`, `comment`, `tags` (JSON), `quote_exact/prefix/suffix`, `page`, `segments` (JSON), `engine_fp`, `anchor_status`, `created_at`, `updated_at`. `pdf_page_notes`: `page`, `x`, `y`, `text`. `pdf_terms`: `word`, `translation`, `context_sentence`, `mastery_level`, `page`, `segments`, `engine_fp`, `anchor_status`. Eski `highlights`/`pdf_notes`/`vocabulary` Faz 8'e kadar durur. Bkz. [[pdfkit]].

## SQLite modu (WAL — 2026-10-13)
Dosya veritabanı her bağlantıda `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`, `wal_autocheckpoint=100` ile açılır (`utils/db_utils.py::configure_sqlite_connection`; bellek içi veritabanında atlanır). WAL kalıcı bir dosya modudur: `pkm_app.db` yanında `-wal`/`-shm` dosyaları görünebilir (uygulama kapanınca temizlenir). Veritabanını elle kopyalarken uygulamayı kapat; yedekleme kodu SQLite backup API'sini kullanır (WAL'ı kapsar). `pdf_text_index.version` 2: eski tavana (2000 sayfa) takılmış belgeler yeniden dizinlenir.

## Hafif Migration
`utils/db_utils.py:_apply_lightweight_migrations()` mevcut SQLite dosyalarına eksik kolonları ekler (idempotent). `init_db()` her başlangıçta önce bunu çağırır, sonra `Base.metadata.create_all` ile yeni tabloları oluşturur. Şu an listedeki tek migration: `resources.is_favorite` kolonu (2026-05-17).

## AI Görevi
SQLAlchemy modelleri `models/` dizini altında ayrı dosyalarda oluştur. İlişkileri `relationship()` + `back_populates` ile çift yönlü tanımla.

## İlgili Sayfalar
[[dizin_yapisi]] · [[core_servisler]] · [[mimari_kurallari]]
