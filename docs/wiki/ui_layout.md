# Arayüz (UI) İskeleti ve Layout

## Genel Mimari: Three-Pane (Master-Detail)

`MainWindow(QMainWindow)` üç sütunlu yapı; sütunlar arası yatay `QSplitter`.

| Sütun | Bileşen | Dosya |
|-------|---------|-------|
| Sol | Sidebar (navigasyon) | `ui/components/sidebar.py` |
| Orta | `ContentWorkspace` (4 sayfa + filter dispatch) | `ui/views/content_workspace.py` |
| Sağ | `DetailView` (3 sayfa stack koordinatörü) | `ui/views/detail_view.py` |

### UI Katmanları (2026-07-06 itibariyle — Okuyucu + Bilgi Havuzu eklendi)

```
MainWindow (ince compose, ~55 satır)
├── Sidebar (3 nav item: Vitrin / Bilgi Havuzu / Ayarlar)
├── ContentWorkspace
│     ├── SettingsView (kategori/etiket CRUD)
│     ├── UrlShowcaseView (tek içerik sayfası — 2 iç görünüm modu, bkz. [[url_vitrin]])
│     ├── ReaderView (kaynağı uygulama içinde okuma — filter-dispatch dışı, open_reader(resource) ile açılır)
│     └── KnowledgePoolView (tüm kaynaklardaki alıntı/kelime — sidebar'dan "knowledge_pool" ile açılır)
└── DetailView (QStackedWidget koordinatörü)
      ├── EmptyDetail (ui/components/empty_detail.py)
      ├── ResourceDetailPanel (ui/components/resource_detail_panel.py)
      └── ResourceForm (ui/components/resource_form.py)

ResourceFlow (ui/controllers/resource_flow.py)
  ↳ event_bus + Workspace/Detail sinyalleri → MainController çağrıları
```

- **MainWindow** sadece pencere iskeletini kurar; iş mantığı yok.
- **ContentWorkspace** `apply_filter(filter_key)` sözlük tabanlı dispatch yapar; `refresh()` aktif filtreyi yeniden uygular.
- **ResourceFlow** UI ile servis arası koordinatör; widget değil, sinyal yönlendirici. `wire()` ile başlatılır.
- **DetailView** ince stack koordinatörü; alt panel sinyallerini aynı isimle dışarı relay eder — dış API kırılmaz.

**Kural:** Hard-coded renk/font yasaktır. Tüm görsel değerler `core/constants/` veya QSS'ten gelir.

---

## Sol — Sidebar (`ui/components/sidebar.py`)

Sabit genişlik: 220 px. Sadece navigasyon — CRUD işlemleri buraya eklenmez.
Navigasyon item'ları qtawesome ikonlarıyla gösterilir; seçili item accent rengine, diğerleri tema ikon rengine döner.

`_STATIC_ITEMS` ile tanımlı 3 nav öğesi (2026-07-03'te "Tüm Kaynaklar" kaldırıldı, 2026-07-06'da "Bilgi Havuzu" eklendi — bkz. [[url_vitrin]]):

| Etiket | Filter Key | Yönlendirme |
|--------|-----------|-------------|
| Bağlantı Vitrini | `"url_showcase"` | UrlShowcaseView — ana sayfa |
| Bilgi Havuzu | `"knowledge_pool"` | KnowledgePoolView — tüm kaynaklardaki alıntı/kelime listesi |
| Ayarlar | `"settings"` | SettingsView — kategori/etiket CRUD |

**Okuyucu (`ReaderView`) sidebar'da YOK** — sabit/context-free bir sayfa değil, belirli bir kaynak için `ResourceDetailPanel`'deki "Oku" butonuyla açılır (`ContentWorkspace.open_reader(resource)`, filter-dispatch dışı bir gecis).

`"inbox"/"planned"/"favorites"` gibi durum bazlı filtreler artık ayrı bir nav öğesi değil — `FilterBar`'ın Durum chip'leri ve Favoriler chip'i üzerinden (hangi sayfada olursa olsun) uygulanır.

Alt kısımda iki `ToggleSwitch` satırı: **Tema Değiştir** ve **Sade Mod**. Sidebar `event_bus.sidebar_filter_changed(filter_key)` yayınlar; `ResourceFlow._on_filter_changed` yakalar → `ContentWorkspace.apply_filter()`. "Sade Mod" toggle'ı `event_bus.simple_mode_toggled(bool)` yayınlar (bkz. [[event_bus]]) — **UrlShowcaseView'ın hangi iç görünümü gösterdiğini değiştirir** (detay: [[url_vitrin]]), kalıcılık yok, oturum içinde bellekte tutulur (tema toggle'ıyla aynı davranış). `set_collapsed()` daraltılmış sidebar'da her iki toggle etiketini de gizler.

---

## Orta — `ContentWorkspace` (QStackedWidget)

`MainWindow._build_ui` içinde `QSplitter`'ın sol widget'ı. Dört sayfa (2026-07-03'te `ContentView` kaldırıldı, bkz. [[url_vitrin]]; 2026-07-06'da Okuyucu + Bilgi Havuzu eklendi):

| Index | Widget | Ne zaman gösterilir |
|-------|--------|---------------------|
| 0 | `SettingsView` | `"settings"` filtresi |
| 1 | `UrlShowcaseView` | Her şey (tek içerik sayfası) |
| 2 | `ReaderView` | `open_reader(resource)` — filter-dispatch dışı, "Oku" butonundan |
| 3 | `KnowledgePoolView` | `"knowledge_pool"` filtresi |

`ContentWorkspace._active_key` her `apply_filter(filter_key)` çağrısında güncellenir (Okuyucu'ya `open_reader()` ile filter-dispatch DIŞINDAN girildiği için bu değeri değiştirmez) — `close_reader()` bu saklanan anahtara göre `apply_filter(_active_key)` çağırarak Okuyucu'yu açmadan önceki gerçek sayfaya (Vitrin/Ayarlar/Bilgi Havuzu) döner.

### SettingsView (`ui/views/settings_view.py`)
`QTabWidget`, iki sekme:
- **Kategoriler:** Chip/grid izgara (`CategoryRow`, `FlowLayout` ile sarmalanır) + alt kısımda inline ekleme formu (ad/renk/ikon). Renk seçimi `ColorPickerButton` ile interaktif yapılır.
- **Etiketler:** Chip/grid izgara (`TagRow`) + inline ekleme formu (ad)

Her `CategoryRow` / `TagRow`: inline düzenle + 2-tıklı sil. `QDialog/QMessageBox` kullanılmaz. Edit moduna geçişte (veya sil-onay metni değişince) satırın genişliği değiştiği için `self.updateGeometry()` çağrılır — bu, sarmalayan `FlowLayout`'a yeniden diziliş yapması gerektiğini bildirir (Qt bunu custom layout'larda otomatik yapmaz).

Düzenle/Sil aksiyonları metin buton yerine `ui/components/icon_action_button.py::IconActionButton` (26x26, `QtAwesomeIcons.EDIT`/`DELETE`, tema-duyarli) kullanir — `card_icon_button.py::_CardIconButton` deseniyle tutarli ama toggle degil sabit-aksiyon butonu. `set_state(icon, color_role, tooltip, object_name)` ile sil-onay durumuna gecilir (ikon ayni kalir, renk `DANGER` → `DANGER_HOVER`, tooltip "Silmek için tekrar tıkla" olur, objectName QSS'in `#RowDeleteConfirmButton` kuralini tetikler). Edit moduna girildiginde sil-onay durumu otomatik sifirlanir (`_reset_delete_button()`) — önceden bu sifirlama sadece `_confirm_pending` bayragini guncelliyor, buton metnini guncellemiyordu (kucuk bir tutarlilik hatasi, bu turda giderildi).

**Kart entegrasyonu:** Grid + ekle-formu artik iki ayri kutu degil, `SettingsView._build_card()`'in kurdugu tek `#SettingsListCard` (`FilterBar`'daki "yukseltilmis kart" deseniyle ayni: `WA_StyledBackground`, `surface_elevated` arka plan, `QGraphicsDropShadowEffect`, tema degisince golge rengi guncellenir). Grid ile ekle-formu arasinda ince `#SettingsCardSeparator` cizgisi var. `#SettingsScrollArea` artik kendi border/arka planini boyamiyor (seffaf) — kartin kendisi cerceveyi cizdigi icin ic ice iki kutu gorunumu olusmuyor. Chip'ler (`#CategoryRow`/`#TagRow`) kartla kontrast olusturmasi icin `{{bg_primary}}` (kartin `{{surface_elevated}}` renginden farkli) kullanir.

**Arama kutusu:** Her kartin ust kisminda (grid'in hemen ustunde) bir `SearchBar` var; `search_changed` sinyali istemci tarafinda isim bazli filtreleme yapar (`SettingsView._filter_rows()` — `row.setVisible()`, DB'ye gitmez). `FlowLayout._do_layout()` gizli widget'lari artik atliyor (`if widget and not widget.isVisible(): continue`) — bu degisiklik olmadan gizlenen satirlar grid'de bos bosluk birakirdi. Yeni kayit eklendiginde (`_reload_categories`/`_reload_tags`) aktif arama metni otomatik olarak yeniden uygulanir, boylece filtre acikken eklenen kayit filtreye uymuyorsa gizli kalir.

**Ortak yardımcı — `ui/components/flow_layout.py::build_flow_stack()`:** Boş-durum etiketi + kaydırılabilir `FlowLayout` izgarası içeren bir `QStackedWidget` kurar (`GRID_PAGE`/`EMPTY_PAGE` sabitleri). Hem `UrlShowcaseView` (rich/simple kart modları) hem `SettingsView` (kategori/etiket grid'i) bu fonksiyonu kullanır — önceden `UrlShowcaseView` içinde özel/private bir fonksiyondu, DRY için ortak bileşene taşındı (2026-07-04).

### UrlShowcaseView (`ui/views/url_showcase_view.py`) — tek içerik sayfası
Detaylı açıklama: [[url_vitrin]]. Özet: **Üst Bar:** `SearchBar` + "Yeni Ekle" butonu — **FilterBar** (`ui/components/filter_bar.py`, "yükseltilmiş navbar kartı" tasarımı, bkz. altındaki not) — **InlineBanner** — içerik alanı `_mode_stack` (`QStackedWidget`, 2 mod): "rich" (varsayılan, `UrlRichCard` + url-only) / "simple" ("Sade Mod" açık, `ResourceCard` + tüm kaynaklar).

**FilterBar görsel tasarımı (2026-07-02):** Gövdeden ayrık "yükseltilmiş navbar kartı" — kendi arka planı (`surface_elevated`), kenarlığı, 12px yuvarlak köşesi ve `QGraphicsDropShadowEffect` gölgesi var (`Colors.SHADOW`, tema değişince güncellenir). `QFrame` alt sınıfı olduğu için QSS `background-color`/`border-radius`'un boyanması `WA_StyledBackground` attribute'una bağlı — bu attribute set edilmeden QSS arka planı yoksayılır (Qt gotcha'sı). Filtre grupları arası ince `#FilterSeparator` ayraçlarla görsel olarak bölünür. "Temizle" butonu hiçbir filtre aktif değilken otomatik devre dışı kalır (`_update_clear_button_state()`). `%RRGGBBAA` (CSS-stili, alfa sonda) tema renklerini Qt'nin beklediği `#AARRGGBB` formatına çeviren `ui/theme_utils.py::to_qcolor()` kullanılır.

**Responsive sarma (2026-07-06):** `FilterBar._build_ui` artık tek satırlık `QHBoxLayout` yerine `ui/components/flow_layout.py::FlowLayout` kullanıyor (kart gridinde zaten kanıtlanmış aynı desen, DRY). Pencere daraldığında kategori/etiket/durum/öncelik kontrolleri kesilmek yerine alt satıra sarıyor. `FlowLayout` stretch desteklemediği için eski `addStretch(1)` kaldırıldı — "Temizle" butonu artık sağa sabitlenmek yerine son chip'in ardından akışa devam ediyor.

**Kart üstü pin/favori:** `PinButton` + `FavoriteButton` (`ui/components/card_icon_button.py`). Tıklama event_bus üzerinden `ResourceFlow → controller.toggle_pin/toggle_favorite`. Pinli kayıt her sorguda en üste gelir.

---

### ReaderView (`ui/views/reader_view.py`) — 2026-07-06

Kaynağın tam metnini (URL'den `trafilatura` ile çıkarılan `full_text`, yoksa kullanıcının kendi `content` notu Markdown render'lı) gösteren, salt-okunur `QTextEdit` tabanlı sayfa. Üst bar: "Geri" butonu (`back_requested` → `ContentWorkspace.close_reader()`) + kaynak başlığı.

**Kindle-tarzı seçim toolbar'ı:** `QTextEdit.selectionChanged` → seçili metin varsa `_SelectionToolbar` (top-level olmayan, child `QFrame`) `cursorRect()` konumuna taşınıp gösterilir. İki buton: "Alıntı olarak kaydet" (seçimi direkt `highlight_save_requested(resource_id, content)` ile kaydeder, sabit `Colors.HIGHLIGHT_COLOR` tema rengiyle anında vurgular) ve "Kelime olarak kaydet" (`_VocabPopover` açar — `resource_form.py`'deki inline kategori-ekleme panelinin aynı deseni, `QDialog` değil: kelime etiketi + çeviri `QLineEdit` + Kaydet/İptal, `vocabulary_save_requested(resource_id, word, translation)` emit eder).

**Mevcut alıntıları yeniden vurgulama:** `load_resource()` her `highlight` için `document().find(highlight.content)` ile arar, bulunursa arka plan rengini uygular. **Bilinen sınırlama:** aynı alt-dizi metinde birden fazla geçiyorsa sadece ilk eşleşme vurgulanır (offset kolonu yok, bilinçli kapsam dışı — bkz. [[veritabani_semasi]]).

**Arka plan tam-metin çıkarma:** `ResourceFlow._schedule_extraction()` (`_ScrapeWorker` ile aynı `QRunnable` deseni, `resource_flow.py`) sadece `url` var VE `full_text` boşsa tetiklenir — her okuyucu açılışında tekrar çekmez. `_on_extract_finished` metni `full_text`'e yazar, okuyucu hâlâ aynı kaynaktaysa (`reader.current_resource_id()` kontrolü — hızlı kaynak değiştirmede yanlış pencereye metin sızmasın diye) `reader.set_full_text()` ile canlı günceller.

### KnowledgePoolView (`ui/views/knowledge_pool_view.py`) — 2026-07-06

`SettingsView` deseniyle `QTabWidget` (Alıntılar/Kelime Dağarcığı sekmesi), her sekmede `SearchBar` + yeni `ui/components/list_stack.py::build_list_stack()` (aşağıya bkz.) ile kurulmuş kaydırılabilir liste. Satırlar `HighlightRow`/`VocabularyRow` (`ui/components/highlight_row.py`/`vocabulary_row.py`, `tag_row.py` deseni ama düzenleme yok — sadece 2-tıklı sil) + kaynak başlığı tıklanabilir link (`resource_clicked` → `resource_jump_requested` → `ResourceFlow._on_resource_jump_requested` → o kaynağın okuyucusunu açar). `event_bus.highlight_added/deleted`/`vocabulary_added/deleted` sinyallerine abone — bir yerde (okuyucuda) alıntı/kelime eklenince/silinince liste otomatik tazelenir.

**Yeni yardımcı — `ui/components/list_stack.py::build_list_stack()`:** `flow_layout.py::build_flow_stack()` ile aynı iskelet (boş-durum + `GRID_PAGE`/`EMPTY_PAGE`), ama `FlowLayout` yerine `QVBoxLayout` kullanır — Highlight/Vocabulary satırları tam-genişlik/değişken-yükseklik olduğu için (chip gibi yan-yana sarmıyor, alt alta diziliyor) `FlowLayout` uygun değil. `add_row(layout, widget)` yardımcı fonksiyonu satırı sondaki `addStretch`'in ÖNCESİNE ekler (`insertWidget(count()-1, ...)`). `clear_list(layout)` — `clear_flow`'un aynı ghost-önleme deseni (`setParent(None)` + `deleteLater()`).

---

## Sağ — DetailView (`ui/views/detail_view.py`)

İnce `QStackedWidget` koordinatörü (~95 satır). Üç sayfa ayrı bileşenlerden gelir:

| Index | Sayfa | Bileşen | Tetikleyici |
|-------|-------|---------|------------|
| 0 | Boş durum | `EmptyDetail` (`ui/components/empty_detail.py`) | `clear()` çağrıldığında |
| 1 | Kaynak görüntüleme | `ResourceDetailPanel` (`ui/components/resource_detail_panel.py`) | `load_resource(resource)` |
| 2 | Kaynak formu | `ResourceForm` (`ui/components/resource_form.py`) | `show_form(...)` / `show_form_edit(...)` |

DetailView yalnızca sayfa geçişini ve sinyal relay'ini yönetir; widget mantığı alt bileşenlerde.

### Görüntüleme paneli (`ResourceDetailPanel`)
- Başlık etiketi (read-only)
- URL butonu (tıklanabilir, tarayıcıda açar) — **2026-07-06:** ham URL yerine `utils/url_utils.py::format_display_url()` ile çıkarılan alan adı (örn. `github.com`) gösterilir, tam URL tooltip'te durur; `#DetailUrlButton` artık düz alt-çizili link değil, `QtAwesomeIcons.OPEN_BROWSER` ikonlu bir "chip/pill" (`tag_badge_bg` arka plan, yuvarlak kenar, hover'da `accent_color` çerçeve)
- Durum `QComboBox` — değişince `status_updated(int, ResourceStatus)` → `ResourceFlow._on_status_updated` (2026-07-06: İlerleme (%) alanı komple kaldırıldı — bkz. [[veritabani_semasi]] — durum artık tamamen bu combo'dan manuel seçilir)
- Notlar `QTextEdit` (düzenlenebilir) + **"Notu Kaydet"** butonu → `content_updated(int, str)` → `ResourceFlow._on_content_updated`
- **"Oku"** butonu (2026-07-06, `#ReadResourceButton`, Düzenle/Sil'in yanına eklendi) → `read_requested(int)` → `ResourceFlow._on_read_requested` → `ContentWorkspace.open_reader(resource)` + arka planda tam metin çıkarma tetiklenir (bkz. yukarıdaki ReaderView bölümü)
- **"Düzenle"** butonu → `edit_requested(int)` → `ResourceFlow._on_edit_requested` → form sayfası dolu açılır
- **"Sil"** butonu → inline 2-tıklı onay → `delete_requested(int)` → `ResourceFlow._on_delete_requested`
- Tema değişiminde `event_bus.theme_changed` panel içinden dinlenir, kapatma ikonu refresh'lenir.

### Form sayfası (index 2) — `ResourceForm`
**Hem ekleme hem düzenleme** için kullanılır (DRY):
- `reset_for_new()` + `load_categories(list)` → yeni kaynak modu (header: "Yeni Kaynak Ekle", status default INBOX)
- `load_resource(resource, categories)` → düzenleme modu (header: "Kaynağı Düzenle", alanlar dolu)
- `submitted(dict)` sinyali: `resource_id` anahtarı varsa güncelleme, yoksa ekleme

`ResourceFlow._on_form_submitted` ayrımı yapar → `controller.add_resource` veya `controller.update_resource`. **Performans notu (2026-07-03):** bu iki controller çağrısı `event_bus.resource_added`/`resource_updated` yayınlar ve bu, `ResourceFlow._on_resource_changed` üzerinden zaten senkron olarak `workspace.refresh()`'i tetikler — `_on_form_submitted` eskiden ayrıca kendi `workspace.refresh()`'ini de çağırıyordu (gereksiz ikinci tam sorgu+kart-yeniden-kurulumu). Bu tekrar kaldırıldı; tek doğruluk kaynağı artık event bus.

**Formdan inline kategori ekleme (2026-07-06):** Kategori alanının yanındaki `+` butonu (`IconActionButton`, `#FormInlineAddButton`) kompakt bir ekle-paneli açar (isim `FormField` + `ColorPickerButton`, aynen [[core_servisler]]'de anlatılan Ayarlar sayfasindaki kategori ekleme deseniyle, ikon alani olmadan). `ResourceForm.category_create_requested(name, color)` → `DetailView` relay → `ResourceFlow._on_category_create_requested` → `controller.create_category(...)` (Ayarlar sayfasindaki ile ayni metot, ayni `event_bus.category_added` emit'i — Ayarlar/FilterBar kategori listeleri de otomatik tazelenir). Basarili olursa `DetailView.set_categories(categories, select_id)` → `ResourceForm.set_categories()` combo'yu tazeler, yeni kategoriyi secili yapar ve ekle-panelini kapatir. Artik kategori eklemek icin Ayarlar sayfasina gitmek zorunlu degil.

---

## Kart Tipleri

| Tip | Dosya | Kullanım |
|-----|-------|----------|
| `ResourceCard` | `ui/components/resource_card.py` | UrlShowcaseView — "simple" mod (Sade Mod açık, tüm kaynaklar) |
| `UrlRichCard` | `ui/components/url_rich_card.py` | UrlShowcaseView — "rich" mod (varsayılan, url-only) |

Kartlar `AccentFrame` tabanlıdır: sol accent şeridi painter ile çizilir, hover durumunda kısa shadow/lift animasyonu alır. `ResourceCard` vurgu rengi kuralı: Kategori rengi > Durum rengi (fallback) şeklindedir. Durum/tag/kategori rozetleri `ColorBadge`, kategori renk önizlemeleri `ColorSwatch` ile çizilir. Her iki kart tipi de tam içerikle render edilir — `ResourceCard`'ın görsel detay gizleyen bir "sade" varyantı yoktur (bkz. [[url_vitrin]]'deki Sade Mod düzeltmesi).

---

## Boş Durum (Empty State)
Sonuç yokken `UrlShowcaseView`'in ilgili moduna ait iç `QStackedWidget`'ı boş-durum sayfasına geçer (`_rich_stack`/`_simple_stack`, her biri kendi `EmptyStateLabel`'ına sahip). `SettingsView`'daki kategori/etiket grid'leri de aynı `build_flow_stack()` deseniyle kendi boş-durum sayfasına sahiptir (`AppStrings.EMPTY_CATEGORIES_MSG`/`EMPTY_TAGS_MSG`).

---

## Sinyaller Özeti (DetailView)

| Sinyal | Tip | Alıcı |
|--------|-----|-------|
| `status_updated` | `Signal(int, object)` | `ResourceFlow._on_status_updated` → `controller.update_resource` |
| `content_updated` | `Signal(int, str)` | `ResourceFlow._on_content_updated` → `controller.update_resource` |
| `form_submitted` | `Signal(dict)` | `ResourceFlow._on_form_submitted` |
| `edit_requested` | `Signal(int)` | `ResourceFlow._on_edit_requested` |
| `delete_requested` | `Signal(int)` | `ResourceFlow._on_delete_requested` |
| `read_requested` | `Signal(int)` | `ResourceFlow._on_read_requested` → `workspace.open_reader(...)` |
| `category_create_requested` | `Signal(str, str)` | `ResourceFlow._on_category_create_requested` |

## İlgili Sayfalar
[[dizin_yapisi]] · [[event_bus]] · [[url_vitrin]] · [[tema_yonetimi]] · [[core_servisler]] · [[veritabani_semasi]]
