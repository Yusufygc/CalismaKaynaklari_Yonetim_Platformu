# Core Servisler ve Repository Katmanı

## Oturum (Session) Yönetimi
- `Session` sınıf içinde **yaratılmaz**; `__init__` üzerinden **enjekte edilir** (test edilebilirlik).
- `commit()` / `rollback()` → **Service katmanı** sorumluluğu.
- Repository sadece `session.add()` / `session.flush()` yapar, transaction yönetmez.

---

## Repository Katmanı (`repositories/`)

### BaseRepository — `repositories/base_repository.py`
Python `TypeVar` + `Generic` ile tüm modellere hizmet veren CRUD sınıfı.

| Metod | İmza |
|-------|------|
| `get_by_id` | `(id: int) -> Model \| None` |
| `get_all` | `() -> list[Model]` |
| `create` | `(obj: Model) -> Model` (flush, commit yok) |
| `update` | `(obj: Model) -> Model` (flush, commit yok) |
| `delete` | `(id: int) -> bool` |

### ResourceRepository — `repositories/resource_repo.py`

| Metod | Açıklama |
|-------|----------|
| `get_by_status(status: ResourceStatus)` | Duruma göre filtrele (inbox/planned/in_progress/completed) |
| `search_by_keyword(keyword: str)` | Başlık/URL/içerik — ILIKE |
| `get_by_category(category_id: int)` | Kategoriye göre filtrele |
| `get_urls_only()` | URL alanı dolu kaynaklar (Vitrin için) |
| `query_filtered(...)` | Kombinasyonel filtre (durum+kategori+etiket+öncelik+favori+url+arama) — `ContentWorkspace` tarafından kullanılan asıl sorgu yolu |

**N+1 önleme (2026-07-03):** Tüm sorgu metotları tek bir private `_base_query()` helper'ından geçer — `joinedload(Resource.category)` + `selectinload(Resource.tags)` ile ilişkiler eager-load edilir. Öncesinde her metot bağımsız `session.query(Resource)` açıyordu; kart render sırasında (`ContentWorkspace._render_resources`, `UrlShowcaseView.load_resources`) her kaynak için `.category`/`.tags` erişimi ayrı bir lazy-load sorgusuna yol açıyordu (N+1). `get_with_tags`/`get_pinned` (sıfır çağrısı olan ölü metotlar) kaldırıldı. **`highlights`/`vocabulary` bilerek bu eager-load setine eklenmedi (2026-07-06):** okuyucu paneli her zaman TEK bir `Resource` tutar (liste değil), bu yüzden `resource.highlights`/`resource.vocabulary` erişimi N+1 değil tek ekstra sorgudur — session app ömrü boyunca açık kaldığı için (`main.py`, bkz. [[mimari_kurallari]]) lazy-load sorunsuz çalışır. `resource_repo.py`'a dokunulmadı.

**Test kapsamı (2026-09-28):** Diğer 5 repository'nin hepsi test edilmişken bu dosyanın hiç dedike testi yoktu (denetimde bulundu) — `tests/test_repositories/test_resource_repo.py` eklendi (16 test): tüm filtre metodları tekil, `query_filtered`'ın kombinasyonları (durum+öncelik birlikte, favori+url birlikte, etiket OR semantiği + `distinct()` tekrar önleme), `set_pinned`/`set_favorite` toggle + not-found durumu.

### HighlightRepository — `repositories/highlight_repo.py`
| Metod | Açıklama |
|-------|----------|
| `get_by_resource(resource_id)` | Kaynağa scope'lu, `created_at.desc(), id.desc()` sıralı (aynı-saniye timestamp çakışmasında `id` tiebreaker — testte yakalandı) |
| `get_all_with_resource()` | Bilgi Havuzu için `joinedload(Highlight.resource)` ile eager-load |

### VocabularyRepository — `repositories/vocabulary_repo.py`
Aynı şekil: `get_by_resource(resource_id)`, `get_all_with_resource()`.

---

## Service Katmanı (`services/`)

### ResourceService — `services/resource_service.py`
**Bağımlılıklar:** `ResourceRepository`, `TagRepository`, `CategoryRepository`

| Metod | Kurallar |
|-------|----------|
| `get_all()` | Tüm kaynaklar |
| `get_by_id(id)` | Bulunamazsa `ResourceNotFoundError` |
| `get_by_status(status)` | `ResourceStatus` enum değeri alır |
| `search(keyword)` | `search_by_keyword` proxy |
| `get_by_category(id)` | Kategoriye göre |
| `get_urls_only()` | URL alanı dolu |
| `add_new_resource(data: dict)` | URL varsa regex doğrula (scheme zorunlu: `https?://`). Kategori ID varsa kontrol et. `tag_names` normalize + dedupe + get-or-create. `extra_metadata` verilmemişse URL metadata çekilir. `flush()` sonra `commit()`. Hata da `rollback()`. |
| `update_resource(id, data: dict)` | Sadece dict'te bulunan anahtarları günceller. URL validasyonu. `tag_names` varsa etiket ilişkilerini tam senkronize eder; boş liste tüm etiketleri kaldırır. `status` artık tamamen manuel (2026-07-06'da `progress` alanı ve ona bağlı otomatik status türetme kaldırıldı). `commit()`. |
| `delete_resource(id)` | Bulunamazsa `ResourceNotFoundError`. Cascade ile etiket linkleri de silinir. |

**URL Validasyonu (`_validate_url`):** `^https?://` zorunlu — scheme'siz URL'ler reddedilir. Ayrı `_URL_RE` regex ile host+path doğrulanır. **İstisna (2026-09-28):** `file://` şemalı URI'ler (yerel PDF içe aktarımı, bkz. aşağıda) `_URL_RE`'den muaf — sadece boş olmayan bir path yeterli, host/domain formatı aranmaz (dosya yolları regex ile host gibi doğrulanamaz).

### ScraperService — `services/scraper_service.py`

| Metod | Açıklama |
|-------|----------|
| `extract_metadata(url)` | `og_title`, `og_description`, `thumbnail`, `favicon` çıkarır. Request/parse hatasında log yazar ve `{}` döndürür. |

**SSRF redirect koruması (2026-09-28):** `is_blocked_host(url)` önceden sadece istek öncesi orijinal URL'e karşı kontrol ediliyordu — `requests.get` varsayılan olarak redirect'leri takip ettiğinden, dışarıdan erişilebilir bir URL iç ağ adresine yönlendirirse guard bunu göremiyordu (TOCTOU/SSRF bypass). `_safe_get()` eklendi: `allow_redirects=False` ile manuel redirect takibi yapıp her hop'ta `is_blocked_host` tekrar çağırıyor, `_MAX_REDIRECTS=5` sınırı var.

### TagService — `services/tag_service.py`

| Metod | Açıklama |
|-------|----------|
| `get_or_create_tag(name)` | Varsa getir, yoksa yarat + commit. Kaynak ekleme akışında kullanılır. |
| `create_tag(name)` | Kullanıcı niyetli — zaten varsa `DuplicateRecordError`. |
| `update_tag(id, new_name)` | Normalize, boşluk+duplicate kontrol, commit. |
| `delete_tag(id)` | Bulunamazsa `ResourceNotFoundError`. |
| `get_all()` | Tüm etiketler |

### CategoryService — `services/category_service.py`

| Metod | Açıklama |
|-------|----------|
| `create_category(name, color_hex, icon)` | HEX format doğrula (`#RRGGBB`). Duplicate → `DuplicateRecordError`. |
| `update_category(id, name, color_hex, icon)` | Aynı doğrulamalar. |
| `delete_category(id)` | İlişkili kaynakların `category_id` → NULL (SET NULL). |
| `get_all()` | Tüm kategoriler |
| `get_by_id(id)` | Tek kategori |

### HighlightService — `services/highlight_service.py` (2026-07-06)
`TagService` deseni (validate → try/commit/log → except/rollback/log.exception/raise). Duzenleme yok — sadece olustur/sil.

| Metod | Açıklama |
|-------|----------|
| `create_highlight(resource_id, content, color=None)` | `content` boşsa `ValidationError`, `resource_id` yoksa `ResourceNotFoundError`. |
| `get_by_resource(resource_id)` / `get_all()` | Kaynağa scope'lu / tüm alıntılar (Bilgi Havuzu) |
| `delete_highlight(id)` | Bulunamazsa `ResourceNotFoundError` |

### VocabularyService — `services/vocabulary_service.py` (2026-07-06)
Aynı desen: `create_vocabulary(resource_id, word, translation, context_sentence=None)` (`word`/`translation` boşsa `ValidationError`), `get_by_resource`/`get_all`, `delete_vocabulary`. `mastery_level` bu turda UI'da yok, model default 0'da kalır.

### ArticleExtractionService — `services/article_extraction_service.py` (2026-07-06, PDF desteği + birleşik indirme 2026-09-28)
`ScraperService`'ten bilerek ayrı: `ScraperService` hafif og:meta scraping yapar, bu servis makalenin gövde metnini HTML olarak çıkarır — farklı sorumluluk/hata modu (`None` döner, dict fallback değil). `extract_full_text(url) -> str | None`.

**PDF desteği (2026-09-28):** URL doğrudan bir PDF'e işaret ediyorsa (`%PDF-` dosya imzası veya `.pdf` uzantısı) `pypdf` ile sayfa-numaralı HTML üretilir (`<h3>Sayfa N</h3><p>...</p>`) — arXiv gibi kaynaklarda artık sadece HTML özet sayfası değil, gerçek tam metin okunabiliyor. Gerçek arXiv PDF'iyle canlı doğrulandı (15 sayfa, 40073 karakter).

**Birleşik indirme + SSRF-redirect düzeltmesi (2026-09-28):** Önceden `trafilatura.fetch_url()` kendi içinde `urllib3 Retry(redirect=...)` ile redirect takip ediyordu ve her hop'ta `is_blocked_host` tekrar çağrılmıyordu (TOCTOU/SSRF riski, backlog'daydı). Artık tek bir `requests`-tabanlı indirme adımı (`core/net_utils.py::safe_http_get` — `ScraperService`'teki `_safe_get` ile aynı, paylaşılan yardımcıya çıkarıldı) her yönlendirme adımında `is_blocked_host`'u tekrar çalıştırıyor; PDF binary içerik de HTML da aynı bu tek adımdan geçiyor, sonra içerik türüne göre `pypdf` veya `trafilatura.extract(output_format="html")`'e dallanıyor.

**Paylaşılan SSRF koruması — `core/net_utils.py::is_blocked_host(url)` + `safe_http_get(...)` (2026-07-06, 2026-09-28 genişletildi):** `ScraperService` ve `ArticleExtractionService`'in kopyalanmış redirect-güvenli indirme döngüleri DRY gereği `core/net_utils.py::safe_http_get`'te birleştirildi.

**Yerel PDF desteği (2026-09-28):** `extract_full_text(url)` çağrılan `url` bir `file://` URI'siyse (`urlparse(url).scheme == "file"`) ağ/SSRF mantığına hiç girilmez — `is_blocked_host` zaten hostname'siz bir `file://` URI'yi otomatik bloklu sayar, bu yüzden dallanma fonksiyonun en başında. `_extract_local_pdf()` diskten doğrudan okuyup aynı `_extract_pdf_html()` yardımcısını kullanır (sıfır yeni PDF-parse kodu). Bu, sürükle-bırak ile içe aktarılan yerel PDF'lerin (bkz. `ui_qml/bridge.py::importLocalPdf`, [[qml_arayuz]]) tam metnini çıkarmak için kullanılıyor.

**Test kapsamı:** `tests/test_core/test_net_utils.py` (SSRF koruması, 13 test), `tests/test_services/test_article_extraction_service.py` (HTML/PDF çıkarım, redirect takibi, SSRF blok, 9+ test).

### PaperMarketService — `services/paper_market_service.py` (2026-09-28)
Konu bazlı akademik makale araması. [OpenAlex Works API](https://api.openalex.org) — ücretsiz, API key yok. Sabit/güvenilir bir host'a sorgu atıldığı için `is_blocked_host` SSRF kontrolüne gerek yok (kullanıcı girdisi arama metni, URL değil). `search(topic) -> {"recent": [...], "popular": [...], "cited": [...]}` — üç ayrı sıralama (`publication_date:desc` / relevance / `cited_by_count:desc`), her biri kendi try/except'inde (biri başarısız olursa diğerleri etkilenmez). `abstract_inverted_index` (OpenAlex'in kelime→pozisyon ters-indeks formatı) düz metne çevrilir. URL seçimi: `pdf_url` → `landing_page_url` → `doi` → hiçbiri yoksa sonuç elenir (kaydedilemeyecek bir sonucu göstermenin anlamı yok). Anonim havuzda 429 (rate limit) canlı testte gözlendi — bir kez kısa bekleyip yeniden dener.

`workers/market_search_worker.py::MarketSearchWorker` ile arka planda (`QThreadPool`) çalıştırılır, `ui_qml/bridge.py::searchArticles`/`saveMarketResult`/`marketResults` üzerinden QML'e bağlanır — bkz. [[qml_arayuz]].

### PdfNoteService — `services/pdf_note_service.py` (2026-09-29)
Native PDF okuyucudaki nokta-bazlı margin notları (`create_note`, `update_note`, `get_by_resource`, `delete_note`) — `HighlightService`'in üçlü katman deseninin (repo/service/controller) birebir kopyası, yeni `models.PdfNote` için. `Highlight`'tan farkı: metin aralığı değil `(page, x, y)` tek nokta + serbest metin tutar. `ui_qml/bridge.py::addPdfNote`/`updatePdfNote`/`deletePdfNote` üzerinden QML'e bağlanır — bkz. [[qml_arayuz]].

**PDF highlight geometrisi — QML kısıtı (2026-09-29, canlı testte keşfedildi):** `QPdfDocument.getSelection()`/`getSelectionAtIndex()` (döndürdüğü `QPdfSelection` degeri) QML script'inden çağrılamıyor (`Unknown method return type: QPdfSelection`). Çözüm: `ui_qml/bridge.py::_load_pdf_document()` + `_highlight_geometry()` bu işlemi Python'da yapıp düz sayı listesi (`boundsPolygons`, `boundingRect`) olarak `_serialize_resource()` üzerinden QML'e gönderiyor. Ayrıca QML'de `Repeater { delegate: ShapePath {...} }` de hata veriyordu (`ShapePath` bir `Item` değil) — `Instantiator` kullanıldı. Bu iki bulgu ileride PDF-render tarafında yeni bir şey eklenirken tekrar karşılaşılabilir, not düşüldü.

---

## Controller Katmanı (`ui/controllers/main_controller.py`)

UI ile service arasındaki köprü. Her method try/except ile sarılır; hata → `event_bus.error_occurred.emit(str(exc))`.

| Metod | Açıklama |
|-------|----------|
| `load_resources_with_filters(filters: dict)` | `ResourceService.query_filtered` proxy — tek filtreleme giriş noktası. (Eski `load_all_resources`/`load_resources_by_filter`/`search_resources` — bunun tarafından süperseslenmiş, sıfır çağrısı olan ölü metotlar — 2026-07-03'te kaldırıldı) |
| `get_resource(id)` | Tek kaynak |
| `add_resource(data)` | `resource_added` emit |
| `update_resource(id, data)` | `resource_updated` emit |
| `delete_resource(id)` | `resource_deleted` emit |
| `load_categories()` / `load_tags()` | Tüm liste |
| `create/update/delete_category(...)` | `category_added/updated/deleted` emit |
| `create/update/delete_tag(...)` | `tag_added/updated/deleted` emit |
| `create_highlight(resource_id, content, color)` / `delete_highlight(id)` | `highlight_added/deleted` emit (2026-07-06) |
| `load_resource_highlights(resource_id)` / `load_all_highlights()` | Kaynağa scope'lu / Bilgi Havuzu için tümü |
| `create_vocabulary(resource_id, word, translation, context_sentence)` / `delete_vocabulary(id)` | `vocabulary_added/deleted` emit |
| `load_resource_vocabulary(resource_id)` / `load_all_vocabulary()` | Kaynağa scope'lu / Bilgi Havuzu için tümü |

---

## Hata Sınıfları — `core/exceptions.py`

| Sınıf | Tetiklenme Koşulu |
|-------|------------------|
| `ValidationError` | Girdi kurallara uymadığında (boş ad, format hatası) |
| `ResourceNotFoundError` | ID'li kayıt bulunamadığında |
| `InvalidURLError` | URL formatı bozuk veya scheme eksik |
| `DuplicateRecordError` | Aynı isimde kategori/tag ekleme girişimi |

## İlgili Sayfalar
[[veritabani_semasi]] · [[dizin_yapisi]] · [[mimari_kurallari]] · [[event_bus]]
