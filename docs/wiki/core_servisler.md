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

**URL Validasyonu (`_validate_url`):** `^https?://` zorunlu — scheme'siz URL'ler reddedilir. Ayrı `_URL_RE` regex ile host+path doğrulanır.

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

### ArticleExtractionService — `services/article_extraction_service.py` (2026-07-06)
`ScraperService`'ten bilerek ayrı: `ScraperService` hafif og:meta scraping yapar, bu servis `trafilatura` ile tüm sayfayı indirip boilerplate-temizleme sezgiseli çalıştırır — farklı sorumluluk/hata modu (`None` döner, dict fallback değil). `extract_full_text(url) -> str | None` — SSRF koruması için `core/net_utils.py::is_blocked_host()` paylaşılır (bkz. aşağıda).

**İndirme timeout'u (2026-09-28):** `trafilatura.fetch_url(url)` öntanımlı olarak kendi `settings.cfg`'sindeki `DOWNLOAD_TIMEOUT=30` değerini kullanıyordu (proje genelinde belgesizdi). Modül seviyesinde `_build_config()` ile `DOWNLOAD_TIMEOUT=10`'a çekilen bir `ConfigParser` her çağrıya `config=` olarak geçiliyor — `ScraperService._TIMEOUT_SECONDS=5` ile aynı disiplin, tam sayfa indirmesi için biraz daha toleranslı.

**Bilinen/kapsam dışı risk:** `trafilatura.fetch_url` kendi içinde `urllib3 Retry(redirect=...)` ile redirect takip ediyor; `ScraperService._safe_get`'teki gibi her hop'ta `is_blocked_host` tekrar çağrılmıyor — aynı TOCTOU/SSRF riski burada da var, henüz düzeltilmedi (ayrı bulgu olarak backlog'da).

**Paylaşılan SSRF koruması — `core/net_utils.py::is_blocked_host(url)` (2026-07-06):** Önceden `ScraperService._is_blocked_host` olarak tek yerde yaşıyordu; `ArticleExtractionService` de aynı korumaya ihtiyaç duyunca `core/net_utils.py`'a çıkarıldı — iki serviste ayrı ayrı tutulup zamanla birbirinden sapması (güvenlik-kritik bir kontrolde) riskini önler.

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
