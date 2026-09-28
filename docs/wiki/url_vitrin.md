# URL Vitrini ve Görsel Kart Sistemi

**Kaynak (Raw Source):** `url_vitrin_layout.md` (kök dizin)

## Modülün Amacı
Web bağlantılarını (URL) metin listesinde kaybetmemek için OpenGraph/meta verilerinden beslenen zengin "Görsel Kartlar" oluşturulur ve "Bağlantı Vitrini" sekmesinde sergilenir.

## Bileşenler

### URL Vitrin Sekmesi — `ui/views/url_showcase_view.py`
- **Uygulamanın açılış (varsayılan) sayfası VE artık tek içerik sayfasıdır.** `main_window.py` başlangıçta `self._sidebar.select_by_key("url_showcase")` + `self._workspace.apply_filter("url_showcase")` çağırır; sidebar'da da "Bağlantı Vitrini" seçili görünür.
- **Vitrinden kaynak ekleme:** Üst barda `SearchBar` + "Yeni Ekle" butonu. `add_requested` sinyali `ContentWorkspace.add_requested`'e relay edilir → `ResourceFlow._on_add_requested` sağ panelde formu açar. Ekleme akışı sayfa-bağımsız çalıştığı için (`DetailView` ayrı bir panel, `_on_form_submitted` sonunda çağırdığı `workspace.refresh()` zaten aktif sayfayı kontrol edip Vitrin'i yeniden yükler) `ResourceFlow`/`MainController` katmanında hiçbir değişiklik gerekmedi.
- `ContentWorkspace._stack` içinde `_PAGE_URL_SHOWCASE = 1` olarak mount edilmiştir (2026-07-03: `ContentView`/"Tüm Kaynaklar" sayfası kaldırıldıktan sonra tek içerik sayfası).
- Sidebar tıklamasıyla da açılır: `Sidebar` → `event_bus.sidebar_filter_changed("url_showcase")` → `ResourceFlow._on_filter_changed` → `ContentWorkspace.apply_filter("url_showcase")` → `_show_url_showcase()` → `view.load_resources(resources)`.

### ⚠️ Düzeltme (2026-07-03): "Sade Mod"un gerçek anlamı — "Tüm Kaynaklar" sayfası birleştirildi

Önceki bir turda "Sade Mod" yanlış anlaşılıp kartlardan görsel detay gizleyen bir toggle olarak uygulanmıştı. Gerçek istek: **ayrı bir "Tüm Kaynaklar" sayfası tamamen kaldırılsın**, Vitrin tek içerik sayfası olarak kalsın; "Sade Mod" toggle'ı bu tek sayfanın **içeriğini** iki mod arasında değiştirsin. `UrlShowcaseView` artık `_mode_stack` (`QStackedWidget`, 2 sayfa) taşır:

| Mod | Ne zaman | İçerik | Filtre |
|-----|----------|--------|--------|
| **rich** (varsayılan, Sade Mod kapalı) | `set_simple_mode(False)` | `FlowLayout` içinde `UrlRichCard` (h_spacing=16, v_spacing=16) | `urls_only=True` — sadece `url` alanı dolu kaynaklar |
| **simple** (Sade Mod açık) | `set_simple_mode(True)` | `FlowLayout` içinde düz `ResourceCard` (h_spacing=12, v_spacing=12) — eski "Tüm Kaynaklar" sayfasının verdiği görünüm | url kısıtı yok — **tüm** kaynaklar |

Akış: `Sidebar` toggle → `event_bus.simple_mode_toggled(bool)` → `ContentWorkspace._on_simple_mode_changed`: `self._simple_mode` günceller, `self._url_showcase.set_simple_mode(enabled)` çağırıp hangi grid'in görüneceğini değiştirir, sonra `refresh()` ile `_show_url_showcase()`'i doğru filtreyle (mod kapalıysa `urls_only=True` eklenir, açıksa eklenmez) yeniden çalıştırır. Her iki mod da aynı ortak `FilterBar` + `SearchBar`'ı paylaşır (`UrlShowcaseView._emit_combined_filters` — `ContentView`'daki eski desenle birebir aynı, `filters["keyword"]` arama metnini ekler).

Sidebar'daki "Tüm Kaynaklar" nav öğesi (`_STATIC_ITEMS`'taki `"all"` anahtarı), `ContentView` sınıfı (`ui/views/content_view.py`) ve `ContentWorkspace`'teki ona özel dispatch mantığı (`_show_content`, `_show_favorites`, `_merged_filters_for_sidebar`, `_render_resources`) tamamen silindi — zaten `sidebar_filter_changed` sinyali sadece `"url_showcase"`/`"settings"` anahtarlarıyla tetikleniyordu, `"inbox"/"planned"/"favorites"/"category:N"` dalları hiçbir UI elemanından ulaşılamıyordu (FilterBar'ın Durum/Favoriler chip'leri zaten aynı işi görüyor). `ResourceCard`'ın bir önceki turda eklenen yanlış `simple=True` (görsel detay gizleme) parametresi de geri alındı — kart her zaman tam içerikle render edilir.

- **Layout:** `FlowLayout` içinde `QScrollArea` (rich: h_spacing=16/v_spacing=16, simple: h_spacing=12/v_spacing=12).

### Zengin URL Kartı — `ui/components/url_rich_card.py`
`QFrame` veya `QWidget` tabanlı, standart `resource_card.py`'dan büyük ve görsel odaklı.

**İç Yapı (yukarıdan aşağıya):**
1. **Kapak Görseli:** Yuvarlatılmış köşeli thumbnail. Yoksa: sitenin favicon'u veya kategorinin büyük+soluk ikonu.
2. **Başlık + Özet:** Meta title (bold, max 2 satır) + meta description (gri, elips).
3. **Alt Bar:** Kategori/etiket rozeti (sol) · "Tarayıcıda Aç" butonu (sağ).

## Görsel Dinamikler
- **Dinamik Çerçeve:** `border-left: 4px solid {kategori/etiket rengi}` — renk kullanıcıya konu kodlaması sunar (Mavi=Yazılım, Yeşil=Finans…).
- **Hover Efekti:** Kartın hafif yukarı kalkması veya DropShadow belirginleşmesi (QSS).
- **Thumbnail:** `extra_metadata.thumbnail` varsa `UrlRichCard` async yükler; hata veya metadata yoksa placeholder ikon kalır. **`ThumbnailWorker` (2026-09-28 önce/sonra):** önceden `urllib.request` + `ssl._create_unverified_context()` (TLS sertifika doğrulaması tamamen kapalıydı) ile, `is_blocked_host` SSRF kontrolü hiç çağrılmadan indiriyordu — `og:image` değeri taranan sayfadan geldiği için saldırgan etkisindeki bir URL'ye korumasız istek riski vardı. `ScraperService._safe_get` ile aynı desene (`requests`, `is_blocked_host` her redirect hop'unda tekrar kontrol, `_MAX_REDIRECTS=5`, varsayılan/açık TLS doğrulaması) geçirildi. Test: `tests/test_components/test_url_rich_card.py`.

## Metadata Akışı
- URL'li kaynak eklendiğinde/güncellendiğinde tarama **arka planda** çalışır (`ResourceFlow._schedule_scrape` → `QThreadPool`), UI thread'i bloklamaz. Sonuç `extra_metadata` olarak DB'ye yazılınca `_on_scrape_finished` kaynağı günceller.
- Çıkarılan alanlar: `og_title`, `og_description`, `thumbnail`, `favicon`.
- Request/parse hataları kaynak kaydını engellemez; boş metadata ile devam edilir. Tarama sırasında beklenmeyen bir istisna olursa `_ScrapeWorker` artık bunu yutmaz — `log.exception(...)` ile loglanır, worker çökmez.

## Bilinen Hata Düzeltmesi: Kart İçinde Metin Ortadan Kesiliyordu

Kart çakışması çözüldükten sonra ayrı bir sorun kaldı: `UrlRichCard`/`ResourceCard` başlık/açıklama etiketleri `setWordWrap(True)` + sabit piksel `setMaximumHeight(70/68/48/34)` kullanıyordu. `setMaximumHeight` piksel cinsinden sert bir clip'tir; bu sabitler fontun `lineSpacing()`'inin tam katı olmadığından son görünür satır **ortadan (yarım glyph)** kesiliyordu. Ayrıca scrape edilen `og_title`/`og_description` ham metni genelde birden fazla `\n` içeriyor, bu da toplam satır sayısını artırıp kesilme ihtimalini büyütüyordu.

**Çözüm:** Yeni `ui/text_utils.py::elide_to_lines(text, font, width, max_lines)` — metni verilen genişlik/fonta göre en fazla `max_lines` satıra diziyor, taşan kısmı `QFontMetrics.elidedText()` ile son satırda "…" ile kesiyor; `text.split()` boşluk/satır-sonu ayrımı yapmadığı için embedded `\n`'leri de düzgün akan tek metne normalize ediyor. Metin taşmıyorsa (ve kaynakta zorlanmış `\n` yoksa) orijinal string aynen döner (string kimliği korunur, testler bunu doğruluyor). `title_label`/`desc_label` artık `elide_to_lines(...)` çıktısıyla oluşturuluyor, `setMaximumHeight` sabit sayı yerine `QFontMetrics(measure_font).lineSpacing() * max_lines` (tam satır, kesme payı sıfır).

**Ölçüm fontu notu:** `QLabel.font()` widget gösterilip QSS uygulanana kadar güvenilir değildir (varsayılan uygulama fontunu döner). Bu yüzden her kartta `_title_measure_font()`/`_desc_measure_font()` — `cards.qss`'teki piksel/weight değerleriyle (UrlRichCard: 15px bold / 12px; ResourceCard: 14px bold / 11px) **birebir eşleşen**, sadece ölçüm amaçlı — bir `QFont` elle oluşturulur. Gerçek render fontu/rengi hâlâ QSS'ten gelir; `cards.qss` bu değerler değişirse senkron tutulmalı. Modül importunda değil, kart construction'ında (instance-level) oluşturulur — QApplication henüz yokken (test collection gibi) modül-seviyesi `QFont()` riskli olurdu.

Satır sınırları: UrlRichCard title=2, desc=3 satır; ResourceCard title=2, desc=2 satır (kart boyutlarına göre ayarlandı).

## Bilinen Hata Düzeltmesi: Kart Eklerken Üst Üste Binme (GERÇEK kök neden — FlowLayout)

Kartların üst üste binmesi/çakışması iki yanlış teşhisten (deferred-delete, DropShadow ghost) sonra gerçek kök nedene indirgendi. Belirtiler: yeni kaynak eklenince kartlar çakışıyor, **bir karta tıklayınca (detay panel açılıp merkez resize olunca) düzeliyor**, sonra tekrar bozuluyor; mod geçişinde ve sıralamada da bozuluyor.

**Gerçek kök neden — `FlowLayout` stale-layout (`ui/components/flow_layout.py`):**
1. `addItem()`/`takeAt()` `self.invalidate()` çağırmıyordu → grid yenilenince (clear + yeni kartlar) layout "dirty" olmuyor, `parentWidget().updateGeometry()` tetiklenmiyor, `QScrollArea` container'ı boyutlandırmıyor, `setGeometry()`/`_do_layout()` çağrılmıyordu. Kartlar dış bir olay (tıklama→panel resize) gelene kadar stale/çakışık kalıyordu.
2. Daha da kritik: `_do_layout()` içindeki `if widget and not widget.isVisible(): continue` satırı (arama filtresi için Faz 4'te eklenmişti) **yeni eklenen henüz-render-edilmemiş kartları da atlıyordu** — parent henüz görünür değilken `isVisible()` False döner → yeni kart hiç `setGeometry` almaz, `(0,0)`'da stale kalıp ilk kartla tam üst üste biner. Offscreen geometri testi bunu sayısal olarak kanıtladı (son kart hep `x=0 y=0`, ilk kartla 311x371 kesişim).

**Çözüm:**
- `addItem()`/`takeAt()` sonuna `self.invalidate()` (dinamik ekle/çıkar sonrası layout'un yeniden hesaplanması için standart davranış).
- `_do_layout()`'ta `not isVisible()` → `isHidden()`: yalnızca bilinçli `hide()` edilmiş (arama filtresi) widget'lar atlanır, yeni eklenenler atlanmaz.
- 2. denemede eklenen yanlış `parentWidget().update()` çağrıları kaldırıldı (`update()` yalnızca repaint, layout hesaplamaz).

Doğrulama: offscreen **geometri** testi — container'ı resize+show, ardışık load/mod-geçişi sonrası hiçbir iki kartın `geometry()`'sinin kesişmediği programatik teyit edildi (fix öncesi kesişme vardı, sonrası yok).

## Bilinen Hata Düzeltmesi: Kart Eklerken Üst Üste Binme (Ghosting)

Yeni kaynak eklendiğinde (özellikle URL'li kaynaklarda, scrape sonucu metadata gelince ikinci bir tam yeniden yükleme daha tetiklendiği için) kartlar bir anlığına üst üste biniyor/hayalet-kopya bırakıyor, sonra bir etkileşimle (hover/scroll) kendiliğinden düzeliyordu.

**İlk (eksik) teşhis:** Grid temizlenirken eski widget'lar `deleteLater()` ile işaretlenip ekranda kaldığı sanıldı; `ui/components/flow_layout.py::clear_flow()` eklenip `deleteLater()`'dan önce `setParent(None)` çağrıldı. Bu, deferred-delete widget'ını hemen koparıyor (iyi bir temizlik) ama **sorunu çözmedi** — smoke testte widget'ın `parent()` gerçekten `None` olmasına rağmen görsel iz kalıyordu.

**Gerçek kök neden — `QGraphicsDropShadowEffect` backing-store ghost:** `AccentFrame` (`ui/components/painted.py`) her karta bir `QGraphicsDropShadowEffect` (gölge) uygular. `QGraphicsEffect`'li widget Qt tarafından offscreen pixmap'e render edilir; kart bir `QScrollArea` container'ının çocuğu olduğundan, yeni kart eklenince `FlowLayout.setGeometry()` tüm kartları yeniden konumlandırır ama eski effect-render'ının viewport'ta kapladığı bölgeyi invalidate etmez → gölge/kart izi bir sonraki tam repaint'e kadar "hayalet" olarak kalır. Widget değil, boyanmış iz olduğu için `setParent(None)` çözmedi.

**Çözüm:** `AccentFrame` idle iken (`_hover_progress <= 0`) `QGraphicsDropShadowEffect`'i `setEnabled(False)` yapar; gölge yalnızca hover'da ("lift" efekti) açılır. Rebuild her zaman tüm kartlar idle iken olduğundan (kullanıcı formu submit ederken imleç kartların üstünde değil), rebuild anında hiçbir kartta offscreen effect render'ı olmaz → ghost kaynağı kurur. Bonus: rebuild başına N effect-render maliyeti sıfırlanır. Sigorta olarak `_load_rich`/`_load_simple`/`_reload_rows` sonunda container `.update()` ile invalidate edilir. `clear_flow()` (setParent+deleteLater) yine de doğru bir temizlik olarak korunur (2026-07-04).

## Bilinen Hata Düzeltmesi: Sayfa Geçişinde Donma

(Tarihsel not — o dönem hâlâ ayrı bir `ContentView` sayfası vardı.) `ContentWorkspace.apply_filter()` her sayfa geçişinde birden fazla `FilterBar.clear()` çağırıyordu; `clear()` sonunda her zaman `filters_changed` sinyalini senkron fırlattığı için `refresh()` **henüz güncellenmemiş eski sayfa index'iyle** tetikleniyordu. Vitrin sayfasından ayrılırken bu, `_show_url_showcase()`'in (tüm kartların yok edilip yeniden kurulması + her biri için yeni ağ isteği) gereksiz yere 2 kez fazladan çalışmasına, dolayısıyla donmaya yol açıyordu. Çözüm: `FilterBar.clear(notify=False)` — `apply_filter()` zaten hemen ardından doğru sayfayı tek seferde yüklediği için ara `refresh()` tetiklemesine gerek yok. Ayrıca `UrlRichCard._on_thumbnail_loaded()` artık ağ/decode hatalarını `log.warning(...)` ile loglar (önceden sessizce yutuluyordu).

## Etkileşim
| Aksiyon | Sonuç |
|---------|-------|
| "Tarayıcıda Aç" butonuna tıkla | `QDesktopServices.openUrl(QUrl(url))` — işletim sisteminin varsayılan tarayıcısı |
| Kartın gövdesine / görseline tıkla | `event_bus.resource_selected.emit(id)` → sağ detay paneli açılır |

## İlgili Sayfalar
[[ui_layout]] · [[event_bus]] · [[veritabani_semasi]] · [[core_servisler]]
