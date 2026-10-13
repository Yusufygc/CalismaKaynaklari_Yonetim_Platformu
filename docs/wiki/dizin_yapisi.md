# Dizin Yapısı ve Modül Haritası

Proje kök dizininde çalışır. Yeni modül/sınıf oluştururken bu yapıya sadık kalınmalıdır.

**Stack:** PySide6 QML (QtQuick 6) · SQLAlchemy 2.0 · SQLite · Alembic

---

## Dizin Ağacı

```text
(repo kökü)/
├── main.py                     # Ana giriş noktası (QML motorunu başlatır)
├── alembic.ini
├── requirements.txt
│
├── assets/
│   └── icons/                  # Özel SVG ikonlar
│
├── core/                       # Yapılandırma, sabitler, temel araçlar
│   ├── config.py
│   ├── user_settings.py        # Kullanıcı ayarları (JSON, atomik): Obsidian vault yolu
│   ├── single_instance.py      # Tek uygulama örneği + örnekler arası mesajlaşma (QLocalServer)
│   ├── protocol_registration.py # Windows HKCU pkm:// protokol kaydı (isteğe bağlı)
│   ├── logger.py
│   ├── exceptions.py
│   ├── events.py               # Event Bus singleton
│   ├── paths.py
│   ├── net_utils.py            # SSRF koruması ve merkezi safe_http_get
│   └── constants/
│       └── strings.py          # AppStrings merkezi metinler ve bildirimler
│
├── workers/                    # Arka plan QRunnable iş parçacıkları (SRP izole)
│   ├── scrape_worker.py        # URL OpenGraph metadata taraması
│   ├── extract_worker.py       # Makale tam metin çıkarma
│   ├── market_search_worker.py # Makale Market (OpenAlex) araması
│   ├── reading_suggestion_worker.py # Kütüphaneden okuma önerileri
│   └── saved_search_worker.py  # Kayıtlı aramalarda yeni yayın kontrolü
│
├── models/                     # SQLAlchemy declarative modelleri
│   ├── base.py
│   ├── category.py
│   ├── tag.py
│   └── resource.py
│
├── repositories/               # Veri erişim katmanı (SQLAlchemy sorguları)
│   ├── base_repository.py
│   ├── resource_repo.py
│   ├── category_repo.py
│   ├── tag_repo.py
│   ├── highlight_repo.py
│   ├── vocabulary_repo.py
│   └── pdf_note_repo.py        # Native PDF satır/nokta notu
│
├── services/                   # İş mantığı ve doğrulama katmanı
│   ├── resource_service.py
│   ├── category_service.py
│   ├── tag_service.py
│   ├── highlight_service.py
│   ├── vocabulary_service.py
│   ├── pdf_note_service.py     # Native PDF satır/nokta notu
│   ├── scraper_service.py      # URL OpenGraph ve meta veri çekici
│   ├── article_extraction_service.py # Zengin HTML / PDF tam metin çıkarıcı
│   ├── paper_market_service.py # OpenAlex API ile akademik makale arama (+ referans/atıf, DOI arama)
│   ├── pdf_download_service.py # Web PDF'ini yerel depoya indirir (native okuyucu için)
│   ├── pdf_storage_service.py  # Yetim PDF dosyası süpürücü
│   ├── citation_service.py     # APA / IEEE / BibTeX atıf üretimi
│   ├── export_service.py       # Alıntı/not/kelime → Markdown dışa aktarım
│   ├── saved_search_service.py # Makale Market kayıtlı aramalar / yeni yayın takibi durumu
│   ├── paper_export_service.py # Market sonuçları → BibTeX / CSV
│   ├── reading_suggestion_service.py # Kütüphanenin ortak referanslarından okuma önerisi
│   ├── library_index.py        # DOI/OpenAlex kimliğiyle kütüphane eşleşmesi (Makale Market rozeti, yinelenen kayıt engeli)
│   ├── metadata_autofill.py    # Künye otomatik doldurma kuralları: yalnız boş alanlar (fill_missing), yanlış makale koruması (titles_conflict)
│   └── schemas.py              # Pydantic modelleri
│
├── controllers/                # UI-agnostik denetleyiciler (Hata yakalama, sinyal fırlatma)
│   ├── resource_controller.py
│   ├── category_controller.py
│   ├── tag_controller.py
│   ├── highlight_controller.py
│   ├── vocabulary_controller.py
│   ├── pdf_note_controller.py
│   └── saved_search_controller.py
│
├── ui_qml/                     # Python ↔ QML köprü katmanı
│   ├── bridge.py               # QmlBridge: ince kabuk / composition root (tema, sayfa, sade mod, toast) + 8 alt-bridge
│   ├── context.py              # BridgeContext + Controllers (DI): controller'lar, thread pool, notifier, PDF/tam metin yardımcıları
│   ├── bridges/                # İş alanı köprüleri (QML: bridge.library / reader / annotations / citations / market / discovery / searches / settings)
│   │   ├── library_bridge.py   # Kaynak listesi/filtre, çekmece, ekle-düzenle-sil (yardımcılar: resource_form, importers, library_events)
│   │   ├── reader_bridge.py    # Okuyucuyu aç/kapat, PDF indirme/anahat, Markdown dışa aktarım
│   │   ├── annotations_bridge.py # Alıntı (HTML/PDF), kelime havuzu, PDF sayfa notları
│   │   ├── citations_bridge.py # Atıf metni, OpenAlex bilgisi, referans/atıf yapanlar
│   │   ├── market_bridge.py    # Makale Market araması/sayfalama/geçmiş, kaydet/dışa aktar (yardımcı: market_saver)
│   │   ├── discovery_bridge.py # Market kart keşfi (referans/atıf/benzer/yazar) ve kütüphaneden öneriler
│   │   ├── searches_bridge.py  # Kayıtlı aramalar ve yeni yayın takibi (durum: saved_search_state)
│   │   ├── settings_bridge.py  # Kategori ve etiket yönetimi
│   │   └── vault_bridge.py     # Obsidian vault klasörü, eşitleme durumu (pdfkit.VaultSync)
│   ├── pdf_files.py            # PdfFileManager: yerel PDF URL/durum, web PDF indirme durumu, silme temizliği (belge açmayı pdfkit yapar)
│   ├── full_text.py            # FullTextExtractor: tam metin çıkarımı (arka plan)
│   ├── notifier.py             # Notifier: tek toast kanalı
│   ├── file_export.py          # write_export: Markdown/BibTeX/CSV dosya yazımı
│   ├── image_provider.py       # IconImageProvider (qtawesome vektörel ikon sağlayıcı)
│   ├── serializers.py          # Model → QML sözlüğü dönüşümleri (saf fonksiyonlar)
│   └── models/
│       └── resource_list_model.py # ResourceListModel (QAbstractListModel)
│
├── qml/                        # Saf QML / QtQuick Arayüzü (Notion/Linear stili)
│   ├── main.qml                # Ana ApplicationWindow
│   ├── theme/
│   │   ├── Theme.qml           # Reaktif Singleton tema motoru (renkler, tipografi)
│   │   └── qmldir
│   ├── components/             # Reusable QML bileşenleri
│   │   ├── AppCard.qml         # Modern zengin kart
│   │   ├── AppSidebar.qml      # Katlanabilir sol navigasyon
│   │   ├── InspectorDrawer.qml # Sağdan kayan detay paneli
│   │   ├── ResourceFormModal.qml # Ekleme/düzenleme modalı
│   │   ├── AppButton.qml
│   │   ├── AppIconButton.qml
│   │   ├── AppBadge.qml
│   │   ├── AppSearchBar.qml
│   │   ├── AppFilterChip.qml
│   │   ├── PaperListItem.qml   # Kompakt makale satırı (Kaynakça sekmesi, keşif listeleri)
│   │   ├── PaperCard.qml       # Makale Market sonuç kartı (rozetler, açılır özet, Kaydet/Kütüphanede)
│   │   ├── HighlightsTab.qml       # Bilgi Havuzu > Alıntılar (etiket filtresi, toplu seçim/silme)
│   │   ├── ContentSearchTab.qml    # Bilgi Havuzu > Metinde Ara (PDF içeriğinde arama, bridge.contentSearch)
│   │   ├── MetadataSettingsPanel.qml # Ayarlar > Künye: künye otomatik doldurma açık/kapalı (bridge.metadata)
│   │   ├── VocabularyTab.qml       # Bilgi Havuzu > Kelimeler
│   │   ├── MarketSearchBar.qml     # Market: konu arama + son aramalar + sekmeler
│   │   ├── MarketFilterBar.qml     # Market: yıl/tür/dil/açık erişim/yazar çipi/öneri düğmesi
│   │   ├── SavedSearchBar.qml      # Market: kayıtlı aramalar çubuğu
│   │   ├── MarketResultsToolbar.qml # Market: toplu seçim, dışa aktar, toplu kaydet
│   │   └── SaveSearchPopup.qml     # Market: aramayı kaydet (koleksiyon etiketi)
│   ├── pdf/                    # PDF okuyucu (pdfkit modellerine bağlı; bkz. [[pdfkit]])
│   │   ├── PdfReaderView.qml   # Native PDF okuyucu (yerel PDF kaynaklar)
│   │   ├── PdfPageArea.qml     # Native PDF render, kaydırma/zoom/arama (Qt PdfMultiPageView temelli)
│   │   ├── PdfSidePanel.qml    # Sayfalar / Anahat / Notlarım / Kaynakça
│   │   ├── PdfSelectionOverlay.qml # Sayfada metin seçilince: renkli alıntı araç çubuğu + kelime çevirisi popover'ı
│   │   ├── PdfHighlightHits.qml    # Kalıcı alıntılara tıklama alanı + renk/yorum/sil düzenleme popover'ı
│   │   └── PdfNoteLayer.qml        # Sayfa notu işaretleri + yeni/düzenle not popover'ları
│   └── views/                  # Sayfa görünümleri
│       ├── ShowcaseView.qml    # Bağlantı vitrini
│       ├── ReaderView.qml      # Dikkat dağıtmayan okuyucu (HTML makaleler)
│       ├── KnowledgePoolView.qml # Bilgi havuzu (alıntılar/kelimeler)
│       ├── SettingsView.qml    # Kategori ve etiket yönetimi
│       └── ArticleMarketView.qml # Makale Market (OpenAlex konu araması)
│
├── pdfkit/                     # Bağımsız PDF modülü (bkz. [[pdfkit]]); dış dünya yalnız pdfkit.api
│   ├── domain/                 # Saf Python: Document, PdfInspection, DOI çıkarımı, hatalar, ReadingState (reading.py)
│   ├── app/                    # Use-case: prepare_pdf, DocumentService, ResourceCatalogPort
│   ├── infra/                  # file_store (CAS), inspector/text (pypdfium2), downloader, orm, repository
│   └── ui/                     # Qt cephesi: PdfLibrary (içe aktarma, indirme, benimseme, çöp toplama), AnnotationListModel/NoteListModel/PageFilterModel, DocumentSession, AnnotationCommands (yazma), PdfBridge (bridge.pdf)
├── scripts/                    # Bakım betikleri (make_lock.py: geçişli requirements.lock üretimi; bench_pdf.py: PDF okuyucu performans ölçümü)
├── migrations/                 # Alembic veritabanı migrasyonları
└── tests/                      # Pytest test paketi
    ├── test_controllers/
    ├── test_qml/               # bridge testleri (test_qml_bridge kabuk/CRUD, test_bridge_market, test_bridge_pdf_files, test_bridge_citations_export) + QML yükleme/sözleşme (test_qml_load) + gerçek fare akışları (test_qml_flows, qml_harness); conftest.py gerçek PDF indirmesini kapatır
    ├── test_repositories/
    ├── test_pdfkit/            # pdfkit birim ve entegrasyon testleri
    ├── test_services/          # conftest.py (`fake_dns`) + http_fakes.py (FakeResponse/FakeRedirectResponse) servis testlerinde ortak
    └── test_core/
```

---

## Katman Kuralları (Hard Rules)

1. **QML Katmanı (`qml/`):** Yalnızca görünüm ve kullanıcı etkileşimini yönetir. Doğrudan veritabanı veya servislere erişmez; tüm işlemler `bridge` (`QmlBridge`) nesnesi üzerinden yürütülür.
2. **Bridge Katmanı (`ui_qml/`):** QML'e Qt Property'leri, `QAbstractListModel` sanallaştırmasını ve Slot'ları sunar. İş mantığını `controllers/` katmanına delege eder.
3. **Controllers Katmanı (`controllers/`):** Kullanıcı girdisini doğrular, `services/` fonksiyonlarını çağırır, UI sınırında hataları yakalar ve `event_bus` sinyalleri fırlatır.
4. **Services Katmanı (`services/`):** İş mantığını barındırır. `session.commit()` ve `rollback()` yalnızca burada yönetilir.
5. **Repositories Katmanı (`repositories/`):** Yalnızca veritabanı sorgularını yürütür, iş mantığı içermez.
