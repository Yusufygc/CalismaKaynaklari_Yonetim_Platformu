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
| full_text | Text | Nullable — okuyucu sayfasında gösterilen ham kaynak metni: URL'den `trafilatura` ile çıkarılan makale gövdesi (2026-07-06, migration `73989d002a5c`). `content`'ten ayrı — biri kullanıcının kendi notu, diğeri kaynağın orijinal metni. **`deferred`** (2026-09-30): liste/filtre sorguları tam metni yüklemez, yalnızca özniteliğe erişilince (okuyucu, `_serialize_resource`) lazy yüklenir |
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

Repo/servis: `repositories/highlight_repo.py::HighlightRepository`, `services/highlight_service.py::HighlightService`. HTML okuyucusunda metin seçilip renk paletinden birine tıklanarak oluşturulur, silinebilir. Native PDF okuyucusunda (`PdfReaderView`, bkz. [[qml_arayuz]]) aynı highlight tablosu kullanılır ama oluşturma `bridge.addPdfHighlight` (page-point koordinatlarından `start_index`/`length` hesaplar) üzerinden, düzenleme (`updateHighlightColor`) + silme reader içinden yapılabilir — manuel ekleme formu hiçbir zaman olmadı.

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

### `pdf_notes` (Native PDF Satır/Nokta Notu — 2026-09-29'da eklendi)
| Alan | Tip | Not |
|------|-----|-----|
| id | Integer PK | |
| resource_id | FK | `resources.id`, `ondelete=CASCADE` |
| page | Integer | Required — 0-bazlı sayfa indeksi |
| x, y | Float | Required — page-point uzayında (PDF nokta birimi, `document.pagePointSize(page)`), çözünürlük/zoom'dan bağımsız |
| note_text | Text | Required |
| created_at | DateTime | |

Repo/servis/controller: `repositories/pdf_note_repo.py::PdfNoteRepository`, `services/pdf_note_service.py::PdfNoteService`, `controllers/pdf_note_controller.py::PdfNoteController` — `Highlight` üçlüsünün (repo/service/controller) birebir aynı iskeleti, yeni model için kopyalandı. `Highlight`'tan kavramsal farkı: bir metin aralığı değil **tek bir nokta** referans alır (native PDF okuyucudaki "Not Ekle" modunda sayfaya tıklanan yer). Sadece o kaynağın PDF okuyucusunda görünür/yönetilir — Bilgi Havuzu'na eklenmedi (cross-resource bir not listesi istenmedi).

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

Repo/servis/controller: `repositories/saved_search_repo.py`, `services/saved_search_service.py` (aynı konu+filtre tekrar kaydedilemez → `DuplicateRecordError`), `controllers/saved_search_controller.py` (+ `MainController` facade). Kaynaklarla ilişkisi yoktur (bağımsız tablo).

## Hafif Migration
`utils/db_utils.py:_apply_lightweight_migrations()` mevcut SQLite dosyalarına eksik kolonları ekler (idempotent). `init_db()` her başlangıçta önce bunu çağırır, sonra `Base.metadata.create_all` ile yeni tabloları oluşturur. Şu an listedeki tek migration: `resources.is_favorite` kolonu (2026-05-17).

## AI Görevi
SQLAlchemy modelleri `models/` dizini altında ayrı dosyalarda oluştur. İlişkileri `relationship()` + `back_populates` ile çift yönlü tanımla.

## İlgili Sayfalar
[[dizin_yapisi]] · [[core_servisler]] · [[mimari_kurallari]]
