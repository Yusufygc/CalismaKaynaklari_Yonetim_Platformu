# Wiki Değişiklik Kayıt Defteri

En yeni girdi her zaman en üstte olmalıdır.

---

## [2026-09-28] REVIEW | resource_repo.py test kapsami eklendi

Bulgu #6: `repositories/resource_repo.py` (proje icindeki en karmasik sorgu, `query_filtered` 53 satir) tek testsiz repository dosyasiydi. `tests/test_repositories/test_resource_repo.py` eklendi — 16 test: `get_all` (pinli-once sirasi), `get_by_status`, `search_by_keyword` (title/url/content ILIKE), `get_by_category`, `get_favorites`, `get_urls_only` (bos-string vs None ayrimi), `query_filtered` kombinasyonlari (durum+oncelik, favori+url, keyword, category_id, etiket OR semantigi + coklu-eslesmede `distinct()` tekrar onleme), `set_pinned`/`set_favorite` (toggle + eksik id'de `None`). 134 test yesil.

Detay: [[core_servisler]].

---

## [2026-09-28] REVIEW | MainController god-object bolundu (5 alt-controller)

Bulgu #5: `MainController` 25 metod tasiyordu (Kaynak+Kategori+Etiket+Alinti+Kelime, 5 farkli alan tek sinifta) — SRP ihlali. Yeni dosyalar: `ui/controllers/resource_controller.py::ResourceController`, `category_controller.py::CategoryController`, `tag_controller.py::TagController`, `highlight_controller.py::HighlightController`, `vocabulary_controller.py::VocabularyController` — her biri kendi Service'ini kurar, ayni "try/except Exception: log.error + event_bus.error_occurred.emit" UI-siniri desenini (bkz. onceki REVIEW girdisi, bu desen kasitli/dogru bulunmustu) tasir.

`MainController` artik sadece `__init__`'te 5 alt-controller'i kurup, ayni 25 public metod imzasiyla delege eden bir facade. **Bilinclii tasarim karari:** her view/flow'a ayri ayri 5 controller enjekte etmek yerine (buyuk blast radius: `main.py`, `ResourceFlow`, `ContentWorkspace`, `SettingsView`, `KnowledgePoolView` — 5+ dosya degisirdi) mevcut tek-`controller`-nesnesi DI deseni korundu, facade sadece delege eder, business logic tasimaz. Sonuc: **hicbir baska dosya degismedi**, `test_main_controller.py`/`test_resource_flow.py` degismeden 118 test yesil kaldi, uygulama offscreen modda calistirilip sema migration + kategori/etiket yuklemesi dogrulandi (crash yok).

Detay: [[mimari_kurallari]].

---

## [2026-09-28] REVIEW | ThumbnailWorker: SSRF korumasi yok + TLS dogrulamasi kapaliydi (kritik)

`except Exception` denetimi sirasinda tesadufen bulunan, plandaki listeye dahil olmayan bulgu: `ui/components/url_rich_card.py::ThumbnailWorker` (og:image thumbnail indirme) `ScraperService`'ten tamamen bagimsiz, ayri bir HTTP istemcisi (`urllib.request`) kullaniyordu ve:
- `is_blocked_host` SSRF kontrolu **hic cagrilmiyordu** — `resource.extra_metadata["thumbnail"]` taranan sayfanin `og:image`/`twitter:image` meta etiketinden geliyor, yani saldirgan etkisindeki bir URL; iç ag/loopback/cloud-metadata adreslerine (`169.254.169.254` vb.) korumasiz istek atilabiliyordu.
- `ssl._create_unverified_context()` ile TLS sertifika dogrulamasi **tamamen kapaliydi** (yorum: "Platform bazli sertifika hatalarini asmak icin") — MITM ile gorsel verisi degistirilebilirdi.

**Duzeltme:** `urllib.request`/`ssl` kaldirildi, `requests` kutuphanesine (proje genelinde zaten kullanilan) gecirildi. `ScraperService._safe_get` ile ayni desen: `_safe_get()` her redirect hop'unda `is_blocked_host` tekrar kontrol ediyor, `_MAX_REDIRECTS=5`, `verify` parametresi hic dokunulmadi (requests varsayilani = sertifika dogrulamasi acik, certifi CA bundle kullanir — platform sertifika deposu sorununu da yan etki olarak cozer).

**Yeni test dosyasi:** `tests/test_components/__init__.py` + `test_url_rich_card.py` (proje ilk kez `ui/components/` icin test icerdi) — basarili indirme, ic adrese blok, redirect-ile-ic-adrese-kacis blok, TLS dogrulamasinin kapatilmadigini dogrulayan 3 test. **Not:** `pkm_app.ui.components.url_rich_card....` string yolu ile monkeypatch, `pkm_app/__init__.py`'daki sys.modules alias mekanizmasi (sadece `core/models/repositories/services/ui/utils` ust seviyesini kapsiyor, `ui.components` gibi iki-hop alt paketleri kapsamiyor) yuzunden basarisiz oldu — modul referansi (`url_rich_card_module.requests`) ile patch edilerek cozuldu; ayni deseni kullanacak gelecekteki `ui/components/` testleri icin not dusuldu.

Detay: [[url_vitrin]] · [[core_servisler]].

---

## [2026-09-28] REVIEW | `except Exception` denetimi + MainController.delete_resource bug fix

Bulgu #4 (38x `except Exception`) tek tek okunarak değerlendirildi — grep sayımı yanıltıcıydı:

**Sonuç: 37/38 site kasıtlı, doğru pattern — bug değil.** Servis katmanındaki 20 site (`resource_service.py`, `tag_service.py`, `category_service.py`, `highlight_service.py`, `vocabulary_service.py`) tutarlı `try/commit → except Exception: rollback + log.exception + raise` deseni — DB commit'i çevreleyen bu geniş yakalama **kasıtlı**: hangi exception türü olursa olsun rollback garanti edilmeli, orijinal exception değişmeden yeniden fırlatılıyor (yutma yok). Daraltmak (`except ValidationError` gibi) yanlış olur — beklenmeyen bir DB hatasında (ör. disk dolu) rollback atlanır. `main_controller.py`'deki 16 site UI sınırı: servisten gelen her exception'ı yakalayıp `event_bus.error_occurred` ile arayüze bildiriyor — bu da kasıtlı, doğru. `resource_flow.py`'deki 2 site (`QRunnable.run()` içinde) arka plan thread güvenliği için aynı şekilde doğru. `resource_card.py`/`theme_utils.py`'deki 2 site qtawesome/SVG render fallback'i — defansif, doğru.

**Gerçek bulunan bug:** `MainController.delete_resource` diğer 12 yazma-metodunun (`add_resource`, `update_resource`, `toggle_pin`, `toggle_favorite`, `create_category`, ... vb.) hepsinde olan `event_bus.error_occurred.emit(str(exc))` çağrısını yapmıyordu — silme başarısız olduğunda kullanıcıya hiçbir geri bildirim gitmiyordu (loglanıyordu ama UI sessiz kalıyordu). Eklendi, `test_main_controller.py`'ye regresyon testi (`test_delete_resource_failure_emits_error`) eklendi.

**Yeni bulunan, henüz dokunulmamış risk (öncelik değerlendirmesi bekliyor):** `ui/components/url_rich_card.py::ThumbnailWorker` — `resource.extra_metadata["thumbnail"]` (scrape edilen sayfanın `og:image`'inden, yani saldırgan etkisindeki bir URL) `urllib.request` ile indiriliyor; `is_blocked_host` SSRF kontrolü **hiç çağrılmıyor** ve `ssl._create_unverified_context()` ile TLS sertifika doğrulaması **tamamen kapalı**. `scraper_service.py`'deki redirect açığından daha ciddi — burada baştan hiç SSRF koruması yok. Ayrı bulgu olarak kullanıcıya bildirildi.

Detay: [[core_servisler]] · [[ui_layout]].

---

## [2026-09-28] REVIEW | SSRF redirect açığı + bağımlılık/timeout düzeltmeleri

Kapsamlı kod denetimi (V2-GenelSablon.md şablonuyla) sonrası bulunan bulguların sıralı düzeltmesi:

**SSRF redirect açığı (Güvenlik):** `ScraperService.extract_metadata` sadece istek öncesi `is_blocked_host(url)` kontrolü yapıyordu; `requests.get` varsayılan redirect takibiyle dışarıdan erişilebilir bir URL iç ağ/loopback adresine yönlendirdiğinde guard bypass ediliyordu. `_safe_get()` eklendi — `allow_redirects=False` + her hop'ta yeniden `is_blocked_host` kontrolü + `_MAX_REDIRECTS=5`. `test_scraper_service.py`'ye 2 yeni test (redirect-to-internal engelleniyor, redirect limiti aşımı engelleniyor).

**requirements.lock eksik paket:** `trafilatura` (`requirements.txt`'de vardı) `requirements.lock`'ta yoktu — pinned kurulum makale çıkarma özelliğinde `ImportError` ile çöküyordu. Ayrıca `trafilatura`'nın kendi bağımlılık listesi `lxml_html_clean`'i çekmiyor (lxml bu modülü ayrı pakete taşıdı) — bu da her iki dosyaya (`requirements.txt`, `requirements.lock`) eklendi. Temiz venv'den `requirements.lock` ile kurulum + tam test suite (114 test) ile doğrulandı.

**article_extraction_service.py timeout:** `trafilatura.fetch_url(url)` açık timeout geçmiyordu (kütüphanenin kendi `DOWNLOAD_TIMEOUT=30` varsayılanına bağımlıydı). Modül seviyesinde `_build_config()` ile `DOWNLOAD_TIMEOUT=10` set edildi, her çağrıya `config=` geçiliyor.

**Ortam:** Bu makinede `C:\Users\ysfygc\anaconda3\envs\KaynakYonetim` conda ortamı yok — proje kökünde `.venv/` (pip venv, zaten `.gitignore`'da) oluşturulup doğrulama buradan yapıldı.

**Kapsam dışı bırakılan (backlog'da kalan):** `article_extraction_service.py`'deki aynı SSRF/redirect riski (trafilatura kendi içinde redirect takip ediyor, `is_blocked_host` hop başına tekrar çağrılmıyor) — ayrı bulgu, henüz dokunulmadı. `except Exception` genişliği, `MainController` god-object riski, test kapsam boşlukları (`resource_repo.py`, `net_utils.py`) — sıradaki adımlar.

Detay: [[core_servisler]].

---

## [2026-07-06] FEAT | Uygulama içi Okuyucu + Bilgi Havuzu (alıntı/kelime)

Kaynağı uygulama dışına çıkmadan okuyup, metin seçerek doğrudan alıntı/kelime çıkarma özelliği eklendi (Kindle/Instapaper tarzı) — önceden planlanan "sağ panelde sekmeli manuel ekleme formu" yaklaşımı kullanıcı tarafından iptal edilip bu yönde revize edildi.

**Veri katmanı:** `Highlight`/`Vocabulary` modelleri ve tabloları zaten vardı (baseline migration'dan beri), hiç kullanılmıyordu — `repositories/highlight_repo.py`/`vocabulary_repo.py` (`tag_repo.py` deseni, `get_by_resource`/`get_all_with_resource` eager-load), `services/highlight_service.py`/`vocabulary_service.py` (`tag_service.py` deseni, validate→commit/rollback) sıfırdan yazıldı. `resources.full_text` (Text, nullable) kolonu eklendi (migration `73989d002a5c`) — kullanıcının kendi notu olan `content`'ten ayrı, kaynağın okunacak ham metni.

**Tam metin çıkarma:** Yeni `services/article_extraction_service.py::ArticleExtractionService` (`trafilatura` bağımlılığı) URL'den makale gövdesini çıkarır — `ScraperService`'ten kasıtlı ayrı (farklı sorumluluk/hata modu). `resource_flow.py`'deki mevcut `_ScrapeWorker` (`QRunnable`) deseni `_ExtractWorker` olarak tekrarlandı, arka planda çalışır. SSRF koruması (`ScraperService._is_blocked_host`) `core/net_utils.py::is_blocked_host()`'a çıkarılıp iki serviste paylaşıldı (güvenlik-kritik kontrol tek yerde).

**UI:** Yeni `ui/views/reader_view.py::ReaderView` — salt-okunur `QTextEdit`, metin seçilince Kindle-tarzı yüzen mini toolbar (`_SelectionToolbar`, top-level olmayan child widget — `QDialog` yasağına uygun) çıkıyor; "Alıntı olarak kaydet" direkt kaydediyor, "Kelime olarak kaydet" çeviri isteyen inline popover (`_VocabPopover`, `resource_form.py`'deki kategori-ekleme panelinin aynı deseni) açıyor. Mevcut alıntılar `document().find()` ile yeniden vurgulanıyor (bilinen sınırlama: aynı alt-dizi tekrar ediyorsa sadece ilk eşleşme). Yeni `ui/views/knowledge_pool_view.py::KnowledgePoolView` — tüm kaynaklardaki alıntı/kelimeleri sekmeli listeleyen, aranabilir, silinebilir yeni bir sidebar sayfası (`ui/components/highlight_row.py`/`vocabulary_row.py`, yeni `ui/components/list_stack.py` — `FlowLayout` yerine `QVBoxLayout` tabanlı liste konteyneri, tam-genişlik satırlar için). `ResourceDetailPanel`'e "Oku" butonu eklendi (`read_requested` → `ContentWorkspace.open_reader(resource)`).

**Bilinmeyen risk, yakalanan bug:** `HighlightRepository`/`VocabularyRepository`'nin `created_at.desc()` sıralaması, ayni saniye içinde eklenen kayıtlarda kararsızdı (SQLite `func.now()` çözünürlüğü) — repo testi bunu yakaladı, `id.desc()` tiebreaker eklendi.

Detay: [[veritabani_semasi]] · [[core_servisler]] · [[ui_layout]] · [[event_bus]] · [[veritabani_migrasyonlari]].

---

## [2026-07-06] FIX+STYLE | Dropdown ok ikonu eklendi + detay panelindeki URL şıklaştırıldı

**Dropdown ok ikonu (FIX):** `QComboBox`'a QSS uygulanınca (bu projede hepsine uygulanıyor) Qt native ok ikonunu tamamen kaybediyor — StatusCombo/FormCombo/FilterCombo hiçbirinde ok yoktu. `assets/icons/chevron_down.svg` (currentColor) eklendi; `theme_manager.py`'daki yeni `_write_themed_svg()` her tema uygulamasında bu SVG'yi o temanın `icon_color`'iyla boyayip `%APPDATA%/PKM/cache/combo_arrow.svg`'ye yaziyor, `base.qss::QComboBox::down-arrow` bu dosyayi `image: url(...)` ile referans veriyor (QSS dosya yolu ister, `load_theme_svg`'nin dondurdugu QIcon degil). Detay: [[tema_yonetimi]].

**URL gösterimi (STYLE):** `ResourceDetailPanel`'deki URL butonu artik ham/uzun URL yerine sadece alan adini (`utils/url_utils.py::format_display_url()`, örn. `github.com`) gösteriyor, tam URL tooltip'te duruyor; duz alt-cizili link yerine `OPEN_BROWSER` ikonlu bir chip/pill gorunumu aldi (`#DetailUrlButton` — `tag_badge_bg` arka plan, yuvarlak kenar, hover'da accent cerceve). Detay: [[ui_layout]].

---

## [2026-07-06] FIX+FEAT | FlowLayout dikey ortalama + formdan inline kategori ekleme

**FlowLayout dikey ortalama (FIX):** `ui/components/flow_layout.py::FlowLayout._do_layout()` her ögeyi satırın en boy'una göre değil, satırın tepesine yapıştırıp kendi `sizeHint` yüksekliğiyle konumlandırıyordu — farklı yükseklikteki etiket/kutu/chip karışımında (örn. FilterBar) satır içi hizasızlık oluşuyordu. Artık layout iki geçişli: önce bir satırın tüm ögeleri toplanıyor, satır tamamlanınca (`flush_row`) her öge `(satır_yüksekliği - öge_yüksekliği) / 2` kadar dikeyde ortalanarak yerleştiriliyor. `FlowLayout` kullanan her yer (FilterBar, kart gridleri, Ayarlar kategori/etiket gridleri) bu düzeltmeden otomatik faydalanıyor.

**Formdan inline kategori ekleme (FEAT):** Önceden yeni kategori sadece Ayarlar sayfasından eklenebiliyordu; "Yeni Kaynak Ekle" formunda kategori yoksa kullanıcı formu terk edip Ayarlar'a gitmek zorundaydı. `ResourceForm`'a Kategori etiketinin yanına bir `+` butonu (`IconActionButton`) eklendi; tıklanınca isim + renk seçiciden oluşan kompakt bir ekle-paneli açılıyor (Ayarlar'daki kategori ekleme deseniyle aynı bileşenler, DRY). Yeni sinyal `ResourceForm.category_create_requested(name, color)` → `DetailView` relay → `ResourceFlow._on_category_create_requested` → mevcut `MainController.create_category(...)` (Ayarlar'ın kullandığı ile birebir aynı metot — aynı `event_bus.category_added` emit'i sayesinde FilterBar/Ayarlar kategori listeleri de otomatik güncelleniyor). Basarili olunca yeni `ResourceForm.set_categories(categories, select_id)` combo'yu tazeliyor, yeni kategoriyi seçili yapıyor ve ekle-panelini kapatıyor.

**Not (ilgisiz, aksiyon alınmadı):** Uygulama loglarında görülen `QFont::setPointSize: Point size <= 0 (-1)` uyarısı proje kodunda hiçbir yerde (`grep -r setPointSize`) bulunmuyor — qtawesome/Qt font-icon motorunun kendi iç uyarısı, zararsız gürültü.

---

## [2026-07-06] FIX | İlerleme (%) özelliği komple kaldırıldı + filtre çubuğu daralınca kesiliyordu

**İlerleme kaldırma:** Sağ detay panelindeki İlerleme (%) `QSpinBox`'ı sadece UI'dan değil, komple sistemden kaldırıldı: `Resource.progress` model kolonu (yeni Alembic migration `6e58af46d8a6` ile `op.batch_alter_table` kullanarak drop edildi — SQLite `DROP COLUMN`'u desteklemiyor), `ResourceUpdateSchema.progress`, `ResourceService._status_for_progress`/`_progress_for_status`/`update_resource_progress`, `MainController.update_progress`, `ResourceDetailPanel`/`DetailView`'daki `progress_updated` sinyali ve wiring'i, `#ProgressSpin` QSS kuralı, `PROGRESS_LABEL` string sabiti. Status artık progress'e bağlı otomatik türetilmiyor — tamamen `Durum` combo'sundan manuel seçiliyor (zaten var olan bir kontrol). Gerçek kullanıcı veritabanı (`%APPDATA%/PKM/pkm_app.db`) yedeklendikten sonra migration uygulandı ve doğrulandı.

**Filtre çubuğu responsive sarma:** `FilterBar` tek satırlık `QHBoxLayout` yerine kart gridinde zaten kullanılan `FlowLayout` deseniyle kuruldu; pencere daraldığında kategori/etiket/durum/öncelik kontrolleri artık kesilmek yerine alt satıra sarıyor.

---

## [2026-07-04] FIX | Kart içinde başlık/açıklama metni ortadan kesiliyordu

`UrlRichCard`/`ResourceCard` başlık/açıklama etiketleri sabit piksel `setMaximumHeight` kullanıyordu; bu deger fontun satır yüksekliğinin tam katı olmadığından son görünür satır yarım glyph ile kesiliyordu (scrape edilen ham metindeki embedded `\n`'ler kesilme ihtimalini artırıyordu). Yeni `ui/text_utils.py::elide_to_lines()` metni en fazla N satıra düzgünce diziyor, taşarsa "…" ile bitiriyor, taşmıyorsa orijinal string'i aynen koruyor (mevcut testler bunu doğruladı). `setMaximumHeight` artık `lineSpacing()*max_lines` (tam satır, sıfır kesme payı). Ölçüm için `cards.qss` değerleriyle senkron tutulması gereken, sadece hesap amaçlı yerel `QFont` kullanılıyor (gerçek render QSS'ten gelmeye devam ediyor).

---

## [2026-07-04] FIX | Kart çakışmasının GERÇEK kök nedeni: FlowLayout stale-layout (3. deneme, çözüldü)

Önceki iki teşhis (deferred-delete, DropShadow ghost) yanlıştı. Gerçek neden `FlowLayout`'ta: (1) `addItem`/`takeAt` `invalidate()` çağırmıyordu, grid yenilenince layout dirty olmuyor, `setGeometry` tetiklenmiyordu; (2) `_do_layout`'taki `not isVisible()` kontrolü (Faz 4 arama filtresi) yeni eklenen henüz-render-edilmemiş kartları da atlıyordu → kart `(0,0)`'da stale kalıp ilk kartla tam üst üste biniyordu. Çözüm: `addItem`/`takeAt`'e `invalidate()`, `_do_layout`'ta `isVisible()` → `isHidden()`. Offscreen geometri testiyle kanıtlandı: fix öncesi son kart hep `(0,0)`, ilk kartla 311x371 kesişim; sonrası 0 çakışma (ekleme/rebuild/mod-geçişi hepsinde). "Tıklayınca düzeliyordu" çünkü panel açılışı merkezi resize edip `setGeometry`'yi tetikliyordu.

---

## [2026-07-04] FIX | Kart ghosting'in GERÇEK kök nedeni: DropShadowEffect (2. deneme)

Bir önceki `clear_flow`/`setParent(None)` düzeltmesi ghosting'i çözmedi. Gerçek kök neden: `AccentFrame`'in her karta uyguladığı `QGraphicsDropShadowEffect`, `QScrollArea` içinde relayout olunca viewport backing-store'da ghost iz bırakıyor (widget değil, boyanmış iz — bu yüzden setParent(None) çözmedi). Çözüm: `AccentFrame` idle iken effect'i `setEnabled(False)` yapıyor (gölge yalnızca hover'da); rebuild anında tüm kartlar idle olduğu için offscreen effect render'ı — dolayısıyla ghost — oluşmuyor. Sigorta: load sonrası container `.update()`. Yan fayda: rebuild başına N effect-render maliyeti sıfırlandı. Davranış değişikliği: kartlar idle'da düz, gölge hover'da beliriyor.

---

## [2026-07-04] FIX | Kaynak/kategori/etiket eklerken kartlar üst üste biniyordu (flicker)

Grid temizlenirken eski widget'lar sadece `deleteLater()` ile işaretleniyordu; gerçek silme Qt event loop'unun sonraki turuna ertelendiği için widget bir-iki frame boyunca eski konumunda görünür kalıyor, yeni eklenen kartla çakışıyordu (özellikle URL'li kaynak eklerken, scrape sonucu ikinci bir tam yeniden yükleme daha tetiklendiği için belirgindi). `ui/components/flow_layout.py::clear_flow()` eklendi — `deleteLater()`'dan önce `setParent(None)` çağırarak widget'ı anında render zincirinden koparıyor. `UrlShowcaseView` (rich/simple) ve `SettingsView` (kategori/etiket) aynı düzeltmeyi kullanıyor.

---

## [2026-07-04] UI | Ayarlar sayfası: Kategori/Etiket arama kutusu eklendi (Faz 4)

Her kartın üstüne `SearchBar` eklendi; istemci tarafında isim bazlı filtreleme yapıyor (DB'ye gitmiyor). `FlowLayout._do_layout()`'a görünürlük kontrolü eklendi (`isVisible()` false olan widget'lar artık boşluk bırakmadan atlanıyor) — bu olmadan arama ile gizlenen chip'ler grid'de boş kare bırakırdı. Yeni kayıt eklenince aktif arama metni otomatik yeniden uygulanıyor. Bu, kullanıcıyla konuşulan Ayarlar sayfası tasarım iyileştirmesinin son fazıydı (Faz 1-4 tamamlandı).

`SettingsView`'daki grid ile alt ekleme formu artık iki ayrı kutu değil, `FilterBar`'daki "yükseltilmiş kart" deseniyle (`WA_StyledBackground`, `surface_elevated`, `QGraphicsDropShadowEffect`) tek `#SettingsListCard` içinde birleşti; aralarında ince `#SettingsCardSeparator` ayracı var. Chip renkleri karta göre kontrast sağlaması için `bg_primary`'ye çevrildi (kartın `surface_elevated` rengiyle çakışmasın diye — ışık temada `bg_secondary` ile `surface_elevated` aynı renk olduğundan `bg_secondary` seçilseydi chip'ler görünmez olurdu, bu ayrıntı fark edilip düzeltildi).

---

## [2026-07-04] UI | Ayarlar sayfası: Düzenle/Sil ikon butona dönüştü (Faz 2)

`CategoryRow`/`TagRow`'daki metin `Düzenle`/`Sil` butonları yeni ortak `ui/components/icon_action_button.py::IconActionButton` bileşeniyle kompakt ikon butonlara (kalem/çöp, `QtAwesomeIcons.EDIT/DELETE`) dönüştürüldü — chip'ler daha kompakt. 2-tıklı sil-onay davranışı korundu (`set_state()` ile ikon/renk/tooltip/objectName güncellenir). Yan etki: edit moduna girildiğinde bekleyen sil-onay durumunun artık görsel olarak da sıfırlandığı bir düzeltme yapıldı (önceden sadece dahili bayrak sıfırlanıyordu).

---

## [2026-07-04] UI | Ayarlar sayfası: Kategori/Etiket listeleri chip/grid izgaraya dönüştürüldü (Faz 1)

Ayarlar sayfasında dikey liste (`CategoryRow`/`TagRow`, tam genişlik) yerine `FlowLayout` tabanlı sarmalanan chip/grid izgara kullanılıyor — boş listeden sonra kalan devasa boş alan sorunu giderildi. `UrlShowcaseView` içindeki özel `_build_grid_stack()` fonksiyonu DRY için `ui/components/flow_layout.py::build_flow_stack()` olarak ortak bileşene taşındı; hem Vitrin hem Ayarlar aynı yardımcıyı kullanıyor. Kategori/etiket için boş-durum mesajları eklendi (`EMPTY_CATEGORIES_MSG`/`EMPTY_TAGS_MSG`). Satır bileşenlerinde edit-mod/sil-onay geçişlerinde `updateGeometry()` çağrısı eklendi (FlowLayout'un yeniden dizilmesi için gerekli). Bu, kullanıcıyla konuşulan çok fazlı Ayarlar sayfası tasarım iyileştirmesinin (ikon butonlar, ekle-formu entegrasyonu, arama kutusu sonraki fazlarda) ilk fazı.

**Ek not:** Bu değişiklikten önce `KaynakYonetim` conda ortamının bozuk/boş olduğu tespit edildi (python.exe/Lib/Scripts yok, `conda-meta` tek kayıt) — `conda create -n KaynakYonetim python=3.11` + `pip install -r requirements.lock pytest` ile yeniden kuruldu.

---

## [2026-07-03] DÜZELTME | "Sade Mod" yanlış anlaşılmıştı — "Tüm Kaynaklar" sayfası kaldırıldı

Önceki turda "Sade Mod" toggle'ı, `ResourceCard`'dan görsel detay (durum rozeti/açıklama/tarih/etiket) gizleyen bir toggle olarak yanlış uygulanmıştı. Gerçek istek farklıydı: ayrı bir "Tüm Kaynaklar" sayfası tamamen kaldırılacak, "Bağlantı Vitrini" tek içerik sayfası olarak kalacak, "Sade Mod" bu tek sayfanın içeriğini değiştirecekti (kapalı: orijinal Vitrin — url-only `UrlRichCard`; açık: eski Tüm Kaynaklar görünümü — tüm kaynaklar, düz `ResourceCard`). Ayrıca Vitrin'e kalıcı bir arama çubuğu eklendi.

Yapılanlar: `ResourceCard`'ın yanlış `simple=` parametresi geri alındı (her zaman tam render). `UrlShowcaseView` artık `_mode_stack` (rich/simple) taşıyor, `set_simple_mode(bool)` ile değiştiriliyor, kendi `SearchBar` + `InlineBanner`'ına sahip. `ContentWorkspace`'ten `ContentView` tamamen çıkarıldı; zaten tamamen ölü olduğu doğrulanan (`sidebar_filter_changed` sinyali sadece `"url_showcase"`/`"settings"` anahtarlarıyla tetikleniyordu) `_show_content`/`_show_favorites`/`_merged_filters_for_sidebar`/`_dispatch` dallı kodu silindi. Sidebar'dan "Tüm Kaynaklar" nav öğesi + ona ait ölü `AppStrings.ALL_RESOURCES`/`QtAwesomeIcons.ALL` sabitleri kaldırıldı. `ui/views/content_view.py` dosyası silindi. `UrlRichCard`'a dokunulmadı — hâlâ aktif olarak kullanılıyor (Sade Mod kapalıyken). Detay: [[url_vitrin]], [[ui_layout]], [[event_bus]]. 87/87 test yeşil, offscreen smoke test ile mod geçişleri (rich↔simple), arama çubuğu, ekleme akışı ve banner'lar uçtan uca doğrulandı.

---

## [2026-07-03] PERF/TEMİZLİK | Kapsamlı debug denetimi: N+1 sorgu, gereksiz yenileme, ölü kod

İki paralel Explore ajanıyla tüm `pkm_app` taranıp bulgular manuel grep ile teyit edildi. Üç somut düzeltme yapıldı:
1. **Gereksiz üçlü yenileme:** `ResourceFlow._on_form_submitted`, `controller.add_resource`/`update_resource`'ın zaten `event_bus.resource_added`/`resource_updated` üzerinden senkron tetiklediği `workspace.refresh()`'i bir daha çağırıyordu — bu tekrarlı çağrı kaldırıldı (kaynak ekleme artık 1 gereksiz tam sorgu+kart-yeniden-kurulumu daha az yapıyor). Detay: [[ui_layout]].
2. **N+1 sorgu:** `ResourceRepository`'deki tüm sorgu metotları artık tek bir `_base_query()` helper'ından geçiyor (`joinedload(category)` + `selectinload(tags)`) — önceden kart render sırasında her kaynak için `.category`/`.tags` erişimi ayrı sorgu açıyordu. `status`/`category_id`/`is_favorite`/`is_pinned`/`url` kolonlarına yeni Alembic migration (`ff016ad9bf6e`) ile index eklendi — `query_filtered` tam bu kolonlarda filtreliyordu, önceden sadece PK indeksliydi. Migration geçici bir kopya DB üzerinde (`DATABASE_URL` env değişkeni ile) autogenerate edilip upgrade/downgrade döngüsüyle doğrulandı, gerçek DB'ye dokunulmadı. Detay: [[core_servisler]], [[veritabani_semasi]], [[veritabani_migrasyonlari]].
3. **Ölü kod temizliği:** Sıfır çağrısı/testi grep ile teyit edilen kod kaldırıldı — `MainController.load_all_resources/load_resources_by_filter/search_resources` (eski filtreleme yaklaşımı, `load_resources_with_filters` tarafından süperseslenmiş), `ResourceRepository.get_with_tags/get_pinned`, `ThemeManager.toggle_theme`, `ContentWorkspace.is_content_active`, `date_utils.format_datetime`, `icons.py::CustomIcons` sınıfı (+ satır 29'daki kopyala-yapıştır `SETTINGS` tekrarı) ve kullanılmayan `QtAwesomeIcons`/`AppStrings` sabitleri (`SEARCH`, `THEME_DARK/LIGHT`, `TAG`, `CATEGORIES`, `TAGS`, 6 adet `ERR_*` çeviri metni), birkaç kullanılmayan import (`theme_manager.py`, `filter_bar.py`, `url_rich_card.py`, `settings_view.py`), `.gitignore`'daki artık geçersiz `graphify-out` satırı. Bilinçli olarak dokunulmayanlar: `tag_service.get_or_create_tag` (test edilmiş servis katmanı public API'si), `core/constants/fonts.py` (CLAUDE.md'nin kanonik font kaynağı kuralı gereği scaffolding olarak korunuyor), `Colors.py`'deki kullanılmayan ~18 Python-taraflı isim takma adı (QSS hâlâ ham anahtarları kullanıyor). 87/87 test yeşil, offscreen smoke test ile refresh sayısındaki azalma ve eager-load sonrası kategori/etiket verisinin doğru render edildiği programatik doğrulandı.

---

## [2026-07-03] UI | Vitrinden kaynak ekleme + "Sade Mod" toggle eklendi

`UrlShowcaseView`'a `ContentView`'daki desenle birebir aynı bir "Yeni Ekle" butonu eklendi (`add_requested` sinyali `ContentWorkspace.add_requested`'e relay edilir); artık ana sayfa olan Vitrin'den başka sayfaya geçmeden kaynak eklenebiliyor. Ekleme akışı zaten sayfa-bağımsız çalıştığı için `ResourceFlow`/`MainController` katmanına dokunulmadı. Ayrıca sidebar'a tema-toggle'ın yanına ikinci bir `ToggleSwitch` — "Sade Mod" — eklendi (`event_bus.simple_mode_toggled(bool)`, yeni sinyal). Açıkken `ResourceCard` (Tüm Kaynaklar sayfası) durum rozeti, açıklama ve tarih/etiket satırını gizleyip sadece kategori ikonu + başlık + pin/favori gösteriyor; Vitrin sayfası (`UrlRichCard`) bu bayraktan etkilenmiyor. Kalıcılık eklenmedi — tema toggle'ı gibi oturum içinde bellekte tutuluyor, projede zaten hiçbir UI tercihi kalıcı değil (YAGNI). Detay: [[ui_layout]], [[url_vitrin]], [[event_bus]]. 87/87 test yeşil, offscreen smoke test ile buton→form→kayıt→Vitrin yenileme zinciri ve sade mod açık/kapalı kart alanları programatik doğrulandı.

---

## [2026-07-02] UI | Katlanabilir Sidebar ve Özel Tema Geçiş Düğmesi (ToggleSwitch) Eklendi

Sidebar daraltılabilir (collapsed: 64px) ve genişletilebilir (expanded: 220px) hale getirildi. Hamburger menü ikonu (`assets/icons/hamburger.svg`) eklenerek sidebar üst kısmına konumlandırıldı. İkonun renginin temayla uyumlu değişmesi için `ui/theme_utils.py` dosyasına `load_theme_svg` eklendi, bu sayede SVG içindeki `currentColor` ifadesi aktif temanın ikon rengiyle dinamik olarak değiştirilmektedir. Geleneksel tema değiştirme butonu, pürüzsüz animasyonlu özel bir `ToggleSwitch` (`ui/components/toggle_switch.py`) bileşeniyle güncellendi. Ayrıca kullanıcının talebi doğrultusunda "Bağlantı Vitrini" (url_showcase) sayfası sidebar menü sıralamasında ilk sıraya getirildi. İlk açılışta hamburger menü ikonunun yüklenmeme sorunu Sidebar constructor'ında aktif tema çağrısıyla düzeltildi; başlangıç varsayılan teması 'light' olarak ayarlandı. Tema geçişlerinin yumuşatılması için `MainWindow` gövdesine 250ms'lik `QGraphicsOpacityEffect` fade-in animasyonu uygulandı. Detay: [[tema_yonetimi]], [[ui_layout]]. 87/87 test yeşil ve programatik geçiş testleriyle doğrulandı.

---

## [2026-07-02] UI | Filtreleme çubuğu "yükseltilmiş navbar kartı" olarak yeniden tasarlandı

`FilterBar` (`ui/components/filter_bar.py`) artık gövdeden görsel olarak ayrık bir kart: kendi arka planı (`surface_elevated`), kenarlığı, 12px yuvarlak köşesi, `QGraphicsDropShadowEffect` gölgesi (tema değişince güncellenir). `QFrame` alt sınıfında QSS arka planının boyanması için gereken `WA_StyledBackground` attribute'u eklendi (önceden set edilmemişti, QSS'teki `background: transparent` olduğu için fark edilmiyordu). Filtre grupları arası `#FilterSeparator` ince ayraçlarla görsel olarak bölündü. Küçük UX iyileştirmesi: "Temizle" butonu hiçbir filtre aktif değilken otomatik devre dışı kalıyor. CSS-stili alfa'lı hex renkleri (`shadow_color` gibi) Qt formatına çeviren `_to_color` fonksiyonu `painted.py`'den `ui/theme_utils.py::to_qcolor()`'a taşındı (DRY, iki bileşen aynı dönüşümü paylaşıyor). Kullanıcıya 3 tasarım seçeneği (navbar kartı / popover menü / navbar+aktif filtre etiketleri) sunuldu, "Yükseltilmiş Navbar Kartı" seçildi. Detay: [[ui_layout]]. 87/87 test yeşil, offscreen ekran görüntüsüyle dark/light tema ve aktif/pasif "Temizle" durumu görsel doğrulandı.

---

## [2026-07-02] FIX | Bağlantı Vitrini ana sayfa yapıldı, sayfa geçişi donması giderildi

Bağlantı Vitrini artık uygulamanın açılış sayfası (`main_window.py`, `Sidebar.select_by_key`). Kök nedeni bulunan donma hatası düzeltildi: `ContentWorkspace.apply_filter()` her geçişte iki `FilterBar.clear()` çağırıyordu, `clear()` sonunda senkron `filters_changed` fırlattığı için `refresh()` eski (henüz değişmemiş) sayfa index'iyle tetikleniyor, Vitrin'den ayrılırken tüm kartlar + ağ istekleri gereksiz yere 2 kez fazladan yeniden kuruluyordu. `FilterBar.clear(notify=False)` parametresiyle çözüldü. Ayrıca iki sessiz hata yutma noktası giderildi: `resource_flow.py`'deki `_ScrapeWorker.run()` artık istisnaları loglar (önceden worker sessizce ölüyordu), `url_rich_card.py`'deki `_on_thumbnail_loaded()` ağ/decode hatalarını `log.warning` ile loglar. Görsellerin DB'de doğru saklandığı (`extra_metadata.thumbnail`) ve `QNetworkAccessManager`+SSL'in ortamda çalıştığı ayrıca doğrulandı — "görseller hiç görünmüyor" şikayetinin ana kaynağı donma hatasıydı. Detay: [[url_vitrin]]. 87/87 test yeşil, offscreen smoke testiyle sayfa geçişi başına tam olarak 1 DB sorgusu yapıldığı doğrulandı (önceden fazladan tetikleniyordu).

---

## [2026-07-02] KALDIRMA | Fikirler (Idea) modülü projeden çıkarıldı

Fikirler modülü tamamen kaldırıldı: `models/idea.py`, `repositories/idea_repo.py`, `services/idea_service.py`, `ui/views/idea_view.py`, `ui/components/idea_card.py`, `ui/components/idea_form.py` ve ilgili testler silindi. Entegrasyon noktaları temizlendi: sidebar nav item, `content_workspace.py` sayfa route'u, `main_controller.py`'deki `load_ideas`/`add_idea`/`update_idea`/`delete_idea`, `event_bus`'taki `idea_added`/`idea_updated`/`idea_deleted` sinyalleri, `resource_flow.py`'deki bağlantılar, `schemas.py`'deki `IdeaUpdateSchema`, `strings.py`/`icons.py`/`status.py`'deki idea'ya özel sabitler (`PRIORITY_LABELS` dahil — `filter_bar.py`'nin kendi ayrı `_PRIORITY_LABELS` listesi olduğu doğrulandı, dokunulmadı). Yeni Alembic revizyonu (`a7d8ff966efd_ideas_tablosunu_kaldir`) `ideas` tablosunu drop eder; gerçek kullanıcı veritabanında uygulandı (1 fikir kaydı kalıcı silindi), `resources`/`categories`/`tags` verisi değişmeden korundu. Detay: [[veritabani_migrasyonlari]]. 87/87 test yeşil (9 idea testi kaldırıldı).

---

## [2026-07-02] MIGRATION | Alembic'e geçiş

`utils/db_utils.py`'deki `Base.metadata.create_all()` + elle yazılmış `_LIGHTWEIGHT_MIGRATIONS` mekanizması Alembic ile değiştirildi. `pkm_app/alembic.ini` + `pkm_app/migrations/` eklendi; `env.py` modelleri import edip `target_metadata = Base.metadata` yapar, DB URL'ini `core.config.settings`'ten okur. İlk revizyon (`3997fe50be13_baseline`) autogenerate ile üretildi (7 tablo). `init_db()` üç senaryoyu ayırt eder: sıfırdan kurulum (`upgrade head`), Alembic-öncesi legacy DB (`stamp head`, şema değişmez), zaten yönetilen DB (bekleyen migration'lar uygulanır). Gerçek kullanıcı DB'sinin kopyası üzerinde doğrulandı: veri birebir korundu, orijinal dosya MD5 ile değişmedi. Detay: [[veritabani_migrasyonlari]]. `alembic>=1.13.0` bağımlılığı eklendi. 3 yeni test (`test_db_utils.py`), toplam paket 96/96 yeşil.

---

## [2026-07-02] PERF | Kaynak eklerken/güncellerken URL taramasını arka plana alma

`ResourceService` artık `ScraperService`'i doğrudan çağırmıyor (bağımlılık kaldırıldı, `_resolve_extra_metadata` helper'ı silindi). URL metadata çıkarımı `ResourceFlow` içinde `QThreadPool`/`QRunnable` ile arka plan thread'inde yapılıyor; sonuç güvenli (kuyruklu) Qt sinyaliyle ana thread'e taşınıp DB'ye yazılıyor. `ResourceFlow`, kuyruklu bağlantı garantisi için `QObject`'e çevrildi. Yavaş/yanıt vermeyen bir siteye kaynak eklerken arayüz artık donmuyor (`add_resource` ~16ms'de dönüyor, önceden ağ isteği bitene kadar bloklanıyordu). 3 yeni entegrasyon testi (`test_resource_flow.py`, gerçek `QThreadPool` ile).

---

## [2026-07-02] REFACTOR | Kaynak/fikir güncelleme akışını Pydantic şemaya taşıma

`ResourceService.add_new_resource`/`update_resource` ve `IdeaService.update_idea` artık tipsiz `dict` yerine yeni `services/schemas.py` içindeki Pydantic modellerini (`extra="forbid"`) kabul ediyor. Formda yazım hatasıyla girilen alan adı artık sessizce yutulmuyor, açık `ValidationError` olarak `MainController` üzerinden kullanıcıya bildiriliyor. `update_resource()` ayrıca alan bazlı yardımcı metodlara bölündü (cyclomatic complexity düşürüldü); davranış değişmedi.

---

## [2026-07-02] TEST | Servis/repo/controller kapsamı genişletme + SSRF koruması

`CategoryService`, `TagService`, repository katmanı (`base`/`category`/`tag`/`idea`) ve `MainController` için hiç test yoktu; validasyon, duplicate, not-found ve `event_bus` sinyal senaryoları eklendi. `ScraperService.extract_metadata` artık hedef hostname'i çözüp loopback/private/link-local adreslere istek atmıyor (SSRF koruması); mevcut scraper testleri gerçek DNS'e bağımlı kalmasın diye otomatik sahte DNS fixture'ı eklendi.

---

## [2026-07-02] FIX | Fikirler modülünü kaynak modülü standardına çekme

`idea_service.py` artık diğer servisler gibi `log.exception` atıyor ve orijinal exception tipini koruyor (önceden her hata `ValidationError`'a sarılıp loglanmadan yutuluyordu). `idea_card.py` hardcoded HEX renkler yerine `resolve_theme_color` ile tema paletini kullanıyor. `Idea` modeli `Mapped[...]`/`func.now()`/`timezone=True` stiline taşındı (Resource ile tutarlı, önceden naive `datetime.utcnow` kullanıyordu), kullanılmayan `to_dict()` kaldırıldı. Öncelik etiketleri (`Yüksek`/`Orta`/`Düşük`) `core/constants/status.py`'de `PRIORITY_LABELS` ile merkezileştirildi. `.gitignore`'daki genel `*.md`/`docs/` kuralı yüzünden hiç commitlenmemiş olan `CLAUDE.md`/`rules.md` git takibine alındı.

---

## [2026-05-17] FIX | UI layout iyileştirmeleri ve vitrin senkronizasyonu

ContentView ve UrlShowcaseView içerisindeki boş durum (empty state) düzen kaymaları QStackedWidget kullanılarak çözüldü. AccentFrame (ResourceCard ve UrlRichCard tabanı) güncellendi: soldaki kalın durum çizgisi kaldırılarak yerine kategori renginde 1px'lik ince bir çerçeve eklendi ve köşeler daha yumuşak (12px) hale getirildi. Vitrin sayfasındayken kaynak silindiğinde ekranın anında güncellenmemesi sorunu, ResourceFlow'daki `is_content_active` kısıtlamasının kaldırılması ve `ContentWorkspace.refresh()` metodunun `SettingsView` yönlendirmelerini koruyacak şekilde güncellenmesiyle çözüldü.

---

## [2026-05-17] FEATURE | Kategori renk picker + ResourceCard kategori rengi

Kategori renk girişleri görselleştirilerek `ColorPickerButton` bileşeni eklendi ve `QColorDialog` entegrasyonu sağlandı. Ayarlar sayfasındaki düz metin (`QLineEdit`) tabanlı renk alanları bu yeni bileşenle değiştirildi. Kart şerit vurgu rengi (`accent_color`) için yeni kural getirildi: `ResourceCard` sol şerit rengi artık öncelikle kategori rengini kullanır, kategori yoksa veya rengi geçersizse eski davranıştaki gibi durum (status) rengine (`fallback`) döner. Yeni QSS kuralları eklendi.

---

## [2026-05-17] FEATURE | Filtreleme + Pin + Favori sistemi

Üç ayrı yetenek tek pakette: (1) `resources.is_favorite` kolonu eklendi; `utils/db_utils.py` içine idempotent lightweight migration helper'ı geldi (`ALTER TABLE` eksik kolonları ekler). (2) `ResourceRepository.query_filtered()` ile kombinasyonel filtre (statuses, category_id, tag_ids, priorities, favorites_only, urls_only, keyword) tek noktada; tüm sorgular `is_pinned desc, created_at desc` ile sıralanır — pinli kayıtlar her listede üstte. `get_favorites()`, `set_pinned()`, `set_favorite()` eklendi. (3) Yeni `ui/components/filter_bar.py` → kategori dropdown + çoklu etiket dropdown + durum chip'leri + öncelik chip'leri + temizle. `ContentView` ve `UrlShowcaseView` üst kısmına eklendi. `ContentWorkspace` artık `_active_filters` state'i tutar, FilterBar sinyallerini dinler, sidebar değişiminde resetler; kategori/etiket CRUD sonrası FilterBar beslemesi otomatik yenilenir. Sidebar'a "Favoriler" nav item'ı (`fa5s.star`); kart üzerine `PinButton` + `FavoriteButton` (yeni `ui/components/card_icon_button.py`). `MainController.toggle_pin/toggle_favorite` + `load_resources_with_filters`. EventBus'a 3 yeni sinyal (`resource_pin_toggle_requested`, `resource_favorite_toggle_requested`, `filters_changed`). Yeni `assets/styles/filters.qss` (tema token'ları, hardcoded HEX yok). 4 yeni service testi eklendi. Test paketi 40/40 geçti.

---

## [2026-05-17] REFACTOR | UI mimari bölünmesi: ContentWorkspace + ResourceFlow + ResourceDetailPanel

MainWindow ve DetailView üç farklı sorumluluğu karıştırıyordu (compose + filter dispatch + flow). UI üç yatay katmana bölündü: (1) **MainWindow** ~55 satır, sadece Sidebar/Splitter/Workspace/DetailView kompozisyonu yapar. (2) Yeni `ui/views/content_workspace.py` → `ContentWorkspace(QWidget)`: main_stack (ContentView/SettingsView/UrlShowcaseView) + sözlük tabanlı `apply_filter` dispatcher + `refresh()`. (3) Yeni `ui/controllers/resource_flow.py` → `ResourceFlow`: UI olmayan koordinatör, event_bus ve DetailView/Workspace sinyallerini MainController çağrılarına çevirir. DetailView ince stack koordinatörüne indirildi; view-page widget'ları `ui/components/resource_detail_panel.py` (`ResourceDetailPanel`) ve `ui/components/empty_detail.py` (`EmptyDetail`) altına çıkarıldı. Alt panel sinyalleri aynı isimle DetailView'den dışarı relay edilir — dış API kırılmadı. Tüm QSS objectName'ler birebir korundu (DetailTitle, DetailCloseButton, StatusCombo, ProgressSpin, NotesEdit, vb.). `test_ui_style_debt.py` `ResourceDetailPanel` import edecek şekilde güncellendi. Test paketi 36/36 geçti.

---

## [2026-05-17] REFACTOR | Exe-uyumlu path katmanı, TR string düzeltmesi, DRY temizliği

`pkm_app/core/paths.py` eklendi: `resource_path()` (frozen ortamda `sys._MEIPASS`, dev'de pkm_app/ kökü) ve `user_data_dir()` (Windows `%APPDATA%/PKM`, macOS `~/Library/Application Support/PKM`, Linux `$XDG_DATA_HOME/PKM`). `config.py`, `theme_manager.py`, `core/constants/icons.py` ve `main.py` bu helper'a taşındı; SQLite DB ve `app.log` artık kullanıcı veri dizinine yazılır, QSS ve ikon klasörü bundle uyumlu çözülür. `main.py` içindeki `sys.path` enjeksiyonu yalnızca dev modunda çalışır. `strings.py` içindeki 38 UI metni doğru Türkçe diakritiklere (ş, ğ, ü, ö, ı, ç, İ) çevrildi. Küçük DRY refaktörleri: `resource_service._resolve_extra_metadata` helper'ı ile add/update arasındaki metadata merge tekrarı kaldırıldı; `settings_view._reload_rows` generic helper'ı `_reload_categories` ve `_reload_tags`'i sadeleştirdi; `detail_view._signals_blocked` context manager'ı blockSignals çiftlerini sarmaladı; `main_window` ve `resource_form` içindeki inline import'lar dosya başına taşındı. Tüm test paketi (36/36) geçti.

---

## [2026-05-15] FIX | Badge alpha renkleri ve vitrin okunabilirligi

Qt tarafinda `#RRGGBBAA` renklerin yanlis yorumlanmasi duzeltildi; sidebar secili arka plani ve hover arka planlari opak tema tokenlarina tasindi. Durum rozetleri artik dogru alpha ile boyanir. URL vitrin karti buyutuldu; thumbnail, baslik, aciklama ve aksiyon satiri daha okunabilir araliklarla render edilir.

---

## [2026-05-15] FIX | URL etiketleri, metadata ve ilerleme senkronu

Devam Ediyor durum rengi amber yerine violet/indigo palete tasindi. Kartlar kaynak aciklamasini veya metadata aciklamasini gosterecek sekilde genisletildi. Detay panelinde durum secenekleri Turkce label'lara baglandi ve ilerleme alani integer yuzdeye cevrildi. Progress/status senkronu servis katmaninda merkezilestirildi. URL'den platform/domain etiketi turetme eklendi; manuel etiketler korunur. Metadata cikarimi OpenGraph, Twitter Card, canonical/favicon/site_name ve YouTube thumbnail fallback kapsami ile guclendirildi.

---

## [2026-05-15] FIX | ColorBadge font weight enum duzeltmesi

`ColorBadge.paintEvent()` icindeki sayisal `QFont.setWeight(650)` kullanimi PySide6 uyumlu `QFont.Weight.DemiBold` enum degerine cevrildi. UI statik testlerine sayisal font weight kullanimini yakalayan kontrol eklendi.

---

## [2026-05-15] UX | Canli profesyonel tema ve mikro etkilesimler

Dark/light paletler canli ama profesyonel renklerle genisletildi (`accent_secondary`, gradient, hover/elevated surface, focus ring, shadow, success/warning tokenlari). Base/sidebar/cards/detail/settings QSS dosyalari gradient primary aksiyonlar, daha net focus/hover state'leri, daha okunakli font fallback zincirleri ve elevated yuzeylerle yenilendi. `AccentFrame` hoverProgress animasyonu ve shadow/lift hissi kazandi. Sidebar nav item'lari qtawesome ikonlariyla gosterilir ve tema/secim rengine gore guncellenir. Stil borcu testlerine tema token esligi ve icon smoke kontrolleri eklendi.

---

## [2026-05-15] FIX | P3 stil borcu temizligi

Tema sozlukleri semantik tokenlarla genisletildi (`danger_*`, `on_accent`, status renkleri, thumbnail/swatch tokenlari). UI kodundaki inline `setStyleSheet` kullanimlari kaldirildi; kart accent seridi, renk rozetleri ve kategori swatch'i painter tabanli `AccentFrame`, `ColorBadge`, `ColorSwatch` bilesenlerine tasindi. QSS dosyalarinda kalan sabit HEX degerleri tema tokenlarina cevrildi. Statik stil borcu testleri ve offscreen Qt widget smoke testleri eklendi.

---

## [2026-05-15] FIX | Veri guvenligi, etiket senkronizasyonu ve URL metadata

Kategori silme davranisinda `delete-orphan` kaldirildi; kaynaklar silinmeden `category_id` NULL olur. SQLite foreign key pragma acildi. `ResourceService` tag listesini normalize/dedupe eder ve `update_resource(..., tag_names=...)` ile etiket iliskilerini tam senkronize eder. `CategoryService`/`TagService` yazma akislari rollback standardina alindi. `ScraperService.extract_metadata()` OpenGraph title/description/image/favicon cikarir; hata durumunda bos metadata ile devam eder. `UrlRichCard` thumbnail URL'lerini Qt network ile async yukler. Paket import smoke testi icin `pkm_app` uyumluluk aliaslari ve pytest kapsami eklendi.

---

## [2026-05-15] FIX | Sayfa yonlendirme + URL Vitrini + Kaynak duzenleme + Code Review

`ResourceStatus.INBOX` eklendi. `load_resources_by_filter` inbox/planned dallari tamamlandi. `UrlShowcaseView` `main_stack`'e mount edildi (index 2), artik `UrlRichCard` ile gosteriyor. `DetailView`: Düzenle/Sil butonlari + 2-tikli sil onayi + "Notu Kaydet" butonu + `edit_requested`/`delete_requested`/`content_updated`/`status_updated` sinyalleri eklendi. `ResourceForm` edit modu (`load_resource`), status alani, priority sirasi Yüksek→Orta→Düşük. `MainController.update_resource`, `search_resources` eklendi. Leaky `_resource_svc` erisimi controller'a tasindi. URL regex schemesiz pattern kaldirild. Dead code (`_on_search` DB sorgusu, `tag:` hasattr hack) temizlendi. `sidebar.py` `theme_changed` baglantisi `_connect_signals`'e tasindi.

---

## [2026-05-15] BUILD | Ayarlar sayfasi + Kategori/Etiket CRUD

`SettingsView(QTabWidget)` iki sekmeli: Kategoriler + Etiketler. Her sekme scroll listesi, `CategoryRow`/`TagRow` inline edit + 2-tikli silme, alt kisminda yeni kayit formu. `MainWindow` QStackedWidget yapisi: `ContentView` (index 0) + `SettingsView` (index 1). Sidebar "Ayarlar" nav item eklendi. `TagService.create_tag` + `update_tag` eklendi. Controller 6 CRUD metod. `event_bus.tag_updated` sinyali. QDialog/QMessageBox: 0.

---

## [2026-05-15] BUILD | Yeni Ekle formu ve inline banner eklendi

`ResourceForm(QFrame)`: title/url/category/priority/tags/content alanları, `submitted(dict)` + `cancelled()` sinyalleri. `InlineBanner(QLabel)`: auto-hide 3.5sn, severity property ile QSS renk seçimi (error=kırmızı, info=accent). `DetailView` → `QStackedWidget` (empty/view/form 3 sayfa), `show_form(categories)` + `form_submitted(dict)` sinyali. `ContentView` inline banner host. `MainWindow._on_add_requested` + `_on_form_submitted` + `_on_error` dolduruldu. `event_bus.error_occurred(str)` sinyali eklendi. QDialog/QMessageBox kullanımı sıfır.

---

## [2026-05-14] BUILD | Kart bileşenleri, URL Vitrini ve QSS tema dosyaları tamamlandı

ResourceCard (240×160, durum rengi sol kenar, etiket rozetleri), UrlRichCard (260×300, thumbnail, og_title/desc, tarayıcıda aç), UrlShowcaseView (FlowLayout). sidebar.qss, cards.qss, detail.qss — tüm renkler {{degisken}} şablonuyla ThemeManager üzerinden enjekte.

---

## [2026-05-14] BUILD | PySide6 UI iskeleti tamamlandı

FlowLayout, SearchBar, Sidebar, ContentView (boş durum dahil), DetailView (URL/durum/ilerleme/notlar), MainWindow (Three-Pane QSplitter), MainController, main.py (init_db + tema + pencere başlatma).

---

## [2026-05-14] BUILD | Service katmanı (iş mantığı) kodlandı

ResourceService: add_new_resource (URL doğrulama, kategori/etiket kontrolü, commit/rollback), update_resource, update_resource_progress (100→COMPLETED), delete_resource. CategoryService: create (HEX doğrulama, duplikat), update, delete. TagService: get_or_create_tag, delete_tag.

---

## [2026-05-14] BUILD | Repository katmanı kodlandı

BaseRepository[T] (Generic CRUD, flush — commit yok). ResourceRepository: get_by_status, search_by_keyword (ILIKE), get_with_tags, get_by_category, get_pinned, get_urls_only. TagRepository: get_by_name. CategoryRepository: get_by_name.

---

## [2026-05-14] BUILD | SQLAlchemy modelleri ve DB yardimcilari kodlandi

`models/`: Base, Category, Tag, Resource (ResourceStatus enum, extra_metadata JSON, priority, progress, is_pinned), Highlight, Vocabulary. N:N: resource_tags_link. Tüm relationship'ler back_populates ile cift yonlu. `utils/db_utils.py`: engine, SessionLocal, init_db(), get_session().

---

## [2026-05-14] BUILD | core/events.py Event Bus kodlandı

`_EventBus(QObject)` Singleton. Sinyaller: resource (added/updated/deleted), category (added/updated/deleted), tag (added/deleted), resource_selected, search_query_changed, sidebar_filter_changed, theme_changed(dict).

---

## [2026-05-14] BUILD | core/ temel yapı taşları kodlandı

`core/config.py` (Pydantic Settings), `core/logger.py` (RotatingFileHandler), `core/exceptions.py` (5 özel hata sınıfı), `core/constants/` (strings, colors, fonts, icons), `core/themes/dark.py` + `light.py`, `core/theme_manager.py` (Singleton, QSS şablon enjeksiyonu), `assets/styles/base.qss` (dinamik tema şablonu).

---

## [2026-05-14] SCAFFOLD | Proje dizin iskeleti ve stub dosyaları oluşturuldu

`pkm_app/` altında tüm klasörler, `__init__.py` dosyaları ve boş stub modüller oluşturuldu.
Kapsam: `core/`, `models/`, `repositories/`, `services/`, `ui/` (controllers/views/components), `utils/`, `tests/`, `assets/`.
Ek: `.env.example`, `pkm_app/main.py` stub.

---

## [2026-05-14] INIT | Wiki anayasası kuruldu, tüm konsept sayfaları oluşturuldu

Kaynak: `rules.md` (anayasa/çalışma kuralları), kök dizindeki 7 mimari `.md` dosyası.
Oluşturulan sayfalar: `index.md`, `mimari_kurallari.md`, `dizin_yapisi.md`, `veritabani_semasi.md`, `core_servisler.md`, `event_bus.md`, `tema_yonetimi.md`, `ui_layout.md`, `url_vitrin.md`.
Düzeltilen kök dosyalar: `event_bus.md` (fence syntax), `tema_yonetimi.md` (outer markdown fence kaldırıldı).
