# QML / QtQuick Arayüz Mimarisi

**Stack:** PySide6 QML (QtQuick 6, QtQuick.Controls, QtQuick.Layouts) · QAbstractListModel · Notion / Linear UI/UX

## Genel Bakış

Sıfırdan **Notion / Linear / Craft** tasarım dilinde akıcı, reaktif ve modern bir QML arayüzü kurulmuştur. Eski QtWidgets arayüzü (`ui/`) kaldırıldı — QML artık projenin **tek** arayüz katmanı. Backend (Repository, Service, Controller, Alembic) katmanına dokunulmamış, Python ↔ QML köprüsü (`QmlBridge`) üzerinden tam entegrasyon sağlanmıştır.

Çalıştırma:
```bash
python main.py
```

---

## 1. Mimari Katmanlar

```text
[QML Arayüzü] (qml/)
  ├── main.qml               -> Ana pencere, Sidebar, Workspace, InspectorDrawer, Modal
  ├── theme/Theme.qml        -> Reaktif Singleton tema motoru (Dark/Light, renkler, tipografi)
  ├── components/            -> AppCard, AppButton, AppIconButton, AppBadge, AppSearchBar, InspectorDrawer, ResourceFormModal...
  └── views/                 -> ShowcaseView, ReaderView, KnowledgePoolView, SettingsView, ArticleMarketView
         ▲
         │ (Signals, Slots, Q_PROPERTY, QAbstractListModel)
         ▼
[Python QML Bridge] (ui_qml/)
  ├── bridge.py              -> QmlBridge(QObject) - State, filtreleme, worker yönetimi
  ├── image_provider.py      -> IconImageProvider - qtawesome ikonlarını image://icon/... üzerinden sunar
  └── models/                -> ResourceListModel(QAbstractListModel) - 60 FPS sanallaştırılmış liste
         ▲
         │
[Mevcut Backend]
  ├── MainController / Sub-Controllers
  ├── Services & Workers
  └── SQLAlchemy Modelleri & SQLite
```

---

## 2. Tasarım & UX Özellikleri (Notion / Linear Tarzı)

1. **Görsel Dil:**
   - 1px ince, net kenarlıklar (`borderSubtle`, `borderStrong`).
   - Katmanlı modern yüzeyler (`bgBase`, `bgSidebar`, `bgSurface`, `bgElevated`, `bgHover`).
   - Reaktif Dark / Light tema geçişi.
2. **Slide-over Inspector Drawer:**
   - Bir karta tıklandığında sağdan pürüzsüz animasyonla açılan detay paneli.
   - Durum hapları (Gelen Kutusu, Planlandı, Devam Eden, Tamamlandı).
   - Harici bağlantı butonu, okuma süresi, etiketler, markdown notlar alanı.
3. **Bağlantı Vitrini (ShowcaseView):**
   - Responsive `GridView` ve `AppCard`.
   - Küçük resim (thumbnail) veya şık gradyan banner fallback'i.
   - Kart üstü pinleme ve favorileme mikro-etkileşimleri.
4. **Dikkat Dağıtmayan Okuyucu (ReaderView):**
   - 760px ortalanmış okuma sütunu.
   - Okuma ilerleme çubuğu, A-/A+ yazı boyutu kontrolleri.
   - Kindle tarzı floating seçim çubuğu: Tek tıkla 5 renkli fosforlu alıntı kaydetme ve kelime havuzuna ekleme.
5. **Bilgi Havuzu (KnowledgePoolView):**
   - Alıntılar ve Kelime Dağarcığı sekmeleri, arama filtresi, kaynağa anında zıplama.
6. **Ayarlar (SettingsView):**
   - Kategori (renk paletli) ve Etiket yönetimi.
7. **Makale Market (ArticleMarketView, 2026-09-28):**
   - Konu bazlı akademik makale keşfi — `services/paper_market_service.py::PaperMarketService`, [OpenAlex Works API](https://api.openalex.org) üzerinden (ücretsiz, API key gerektirmiyor).
   - Üç sonuç listesi: **En Güncel** (`sort=publication_date:desc`), **En Popüler** (OpenAlex relevance sıralaması, sort parametresi verilmez), **En Çok Atıf Alan** (`sort=cited_by_count:desc`), her biri 10 sonuç.
   - Arama sadece Enter/"Ara" butonuyla tetiklenir — `AppSearchBar` bilinçli olarak kullanılmadı çünkü o bileşen her tuş vuruşunda sinyal fırlatıyor; uzak API rate-limitli (canlı testte 429 gözlendi, `PaperMarketService` bunu 1 kez kısa bekleyip yeniden deneyerek tolere ediyor).
   - Her sonuç satırında başlık, yazarlar+yıl, atıf rozeti, özet (OpenAlex'in `abstract_inverted_index` ters-indeksinden düz metne çevrilir) ve tek tıkla "Kaydet" — kaydedilen makale normal kaynak akışına (`bridge.saveMarketResult` → `add_resource` → arka planda `ExtractWorker` ile tam metin çıkarımı) girer, "Oku" ile hemen okunabilir hale gelir.
   - Yazar/yıl/atıf sayısı `extra_metadata.source: "openalex"` ile birlikte saklanır; kategori/etiket ataması yok (manuel formdan farklı, daraltılmış kaydetme yolu).
8. **Yerel PDF Sürükle-Bırak (2026-09-28):** `qml/main.qml` root penceresinde tüm pencereyi kaplayan bir `DropArea` — sürükleme sırasında (`containsDrag`) yarı saydam bir overlay ("PDF'i buraya bırak") gösterir. Bırakılan her `.pdf` dosyası için `bridge.importLocalPdf(fileUrl)` çağrılır: dosya `core/paths.py::pdf_storage_dir()` (`%APPDATA%/PKM/pdfs/`) altına benzersiz bir adla **kopyalanır** (orijinale dokunulmaz), `resources.url`'e standart bir `file:///...` URI'si yazılır. Bu tasarım kararı sayesinde tüm mevcut okuyucu/extraction altyapısı (arka plan `ExtractWorker`, "Tarayıcıda Aç" butonu, `ReaderView`'daki HTML render) **hiç değişmeden** yerel PDF'lerle de çalışır — `ArticleExtractionService` sadece ağ yerine diskten okuyacak şekilde dallanıyor (bkz. [[core_servisler]]). Birden fazla dosya aynı anda bırakılabilir, her biri ayrı kaynak olur.
9. **Sade Görünüm Modu (ShowcaseView, 2026-09-28):** Vitrin üst araç çubuğundaki iki durumlu görünüm seçici (`fa5s.th-large` Zengin, `fa5s.th-list` Sade) ile kartların görsel yoğunluğu değiştirilir. Sade modda 120px kapak görseli gizlenir, sol kenara kategori renk şeridi eklenir, kart yüksekliği 290px'den 136px'e düşer (`cellHeight` 305px -> 148px) ve ekrandaki kaynak yoğunluğu 2 katına çıkar.
10. **Native PDF Okuyucu (PdfReaderView, 2026-09-29):** Yerel (`file://`) PDF kaynakları artık `pypdf` ile metne çevrilmiş HTML değil, gerçek PDF sayfa render'ıyla açılıyor — `bridge.openReader()` `resource.url`'nin `file://...pdf` olduğunu görünce `currentView`'i `"reader"` yerine `"pdfReader"` yapıyor (web'den PDF'ler — arXiv gibi — hâlâ eski metin-okuyucuda, `QPdfDocument.source` ağdan indirme yapmıyor çünkü).
    - **Render**: `qml/components/PdfPageArea.qml`, Qt'nin `QtQuick.Pdf` modülündeki `PdfMultiPageView.qml`'i temel alan kopyala-değiştir bileşeni (Qt dokümantasyonu bunu öneriyor) — sürekli kaydırmalı çok-sayfalı görünüm, pinch/wheel zoom, sayfa içi link tıklama, metin seçimi hepsi Qt'nin kendi altyapısından.
    - **Highlight (oluştur/düzenle/sil)**: Metin seçilince `Theme.highlightPalette`'ten (aynı 5 renk, HTML okuyucuyla ortak) renk seçme toolbar'ı çıkar. **Önemli kısıt (çalışma zamanında keşfedildi):** QML script'inden `QPdfDocument.getSelection()`/`getSelectionAtIndex()` çağrılamıyor (`Unknown method return type: QPdfSelection` hatası) — bu yüzden QML sadece seçimin `from`/`to` noktalarını (page-point uzayında) `bridge.addPdfHighlight(...)`'a yolluyor, `QPdfSelection` ile ilgili TÜM işlem (`startIndex`/`endIndex`/`bounds`) Python tarafında (`ui_qml/bridge.py::_load_pdf_document`/`_highlight_geometry`) yapılıyor. Kalıcılık piksel değil **karakter-index** bazlı (`highlights.start_index`/`length`, `page_number` — nullable, sadece PDF highlight'larında dolu) — zoom/scroll'dan bağımsız, `getSelectionAtIndex(page, start_index, length)` ile her seferinde yeniden hesaplanıyor. Geometri (`boundsPolygons`/`boundingRect`) `_serialize_resource()`'ta önceden hesaplanıp QML'e düz sayı listesi olarak gönderiliyor; QML tarafında `Repeater`+`ShapePath` de çalışmıyordu (`ShapePath` bir `Item` değil, "Delegate must be of Item type") — `Instantiator` kullanıldı. Var olan bir highlight'a tıklayınca aynı palet + Sil butonu içeren bir popover açılıyor (`bridge.updateHighlightColor`/`deleteHighlight`).
    - **Satır Notu (yeni, Highlight'tan bağımsız)**: Üst bardaki "Not Ekle" toggle'ı aktifken sayfaya tıklamak (`TapHandler`) o noktada (page-point, çözünürlükten bağımsız) bir metin popover'ı açar → `bridge.addPdfNote(resourceId, page, x, y, text)`. Kalıcı notlar küçük bir ikon (`fa5s.comment-alt`) olarak o noktada görünür, tıklayınca düzenle/sil popover'ı açılır. Yeni `models.PdfNote` tablosu (`repositories/pdf_note_repo.py`, `services/pdf_note_service.py`, `controllers/pdf_note_controller.py` — `Highlight`'ın üçlü katman deseninin birebir kopyası).
    - **Kapsam dışı (bilinçli)**: Sadece yerel PDF'ler native render alıyor; PDF dosyasının kendisine gerçek annotation gömülmüyor (highlight/not veritabanımızda, dosya hiç değişmiyor); Bilgi Havuzu'na PDF notu eklenmedi (sadece o kaynağın okuyucusunda yönetiliyor).

