# pdfkit — PDF Okuma ve Çalışma Modülü

Bağımsız paket (`pdfkit/`). Plan: `docs/plans/pdfkit-plan-2026-10-12.md` · Faz 0–1 raporları: `docs/plans/pdfkit-faz0-raporu.md`, `docs/plans/pdfkit-faz1-raporu.md`. Durum: **Faz 2 tamam** (belge deposu + alıntı alanı ve çapa çözümleyici); UI veri akışı, vault sonraki fazlar.

## Sınır kuralları

- Uygulamanın geri kalanı yalnız `pdfkit.api` kullanır. `pdfkit`, `services/`, `controllers/`, `ui_qml/` import etmez.
- Paylaşılan çekirdek (`core`) ve ortak `Base` (`models.base`) bilinçli istisnadır.
- Uygulamanın kaynak (`Resource`) kayıtlarına erişimi `pdfkit.app.ports.ResourceCatalogPort` arayüzüdür; uygulama tarafı `ui_qml/pdf_catalog.py::ResourceCatalog`.
- Katmanlar: `domain/` (saf Python) → `app/` (use-case) → `infra/` (SQLite, dosya deposu, PDFium) → `ui/` (Qt cephesi). Bağlantılar: [[mimari_kurallari]], [[core_servisler]].

## Belge deposu (Faz 1)

- **İçerik adresli depo:** `<veri>/pdfs/store/ab/<sha256>/<okunur-ad>.pdf` (`pdfkit/infra/file_store.py`). Aynı içerik tek dosyadır; dizin adı SHA-256, dosya adı ilk görülen ad (Windows'ta güvenli, ≤60 karakter) — kartlarda hash değil dosya adı görünür. Yazma atomiktir (geçici dosya + `os.replace`).
- **Veritabanı:** `pdf_documents` (sha256 benzersiz, göreli yol, sayfa sayısı, `has_text_layer`, PDF başlığı/yazarı, DOI, kaynak türü) ve `pdf_resource_documents` (kaynak → belge; aynı PDF birden çok kaynakta olabilir). Migration `b3a91c5d7e20`. Bkz. [[veritabani_semasi]], [[veritabani_migrasyonlari]].
- **İçe aktarma:** `PdfLibrary.import_local` (`pdfkit/ui/library.py`): arka planda `prepare_pdf` (PDFium incelemesi → SHA-256 → depoya kopya; kaynak dosyaya dokunulmaz), ana thread'de kayıt. Aynı içerik zaten varsa ikinci kaynak oluşmaz (`duplicate`). Bozuk/şifreli dosya `invalid`.
- **İnceleme (`infra/inspector.py`, pypdfium2):** sayfa sayısı, metin katmanı var mı (ilk 5 sayfa), PDF başlığı/yazarı (sahte başlıklar atılır), DOI (metadata, sonra ilk 2 sayfa). Metin katmanı yoksa kullanıcıya bildirim gösterilir. PDFium thread-safe olmadığı için tüm pypdfium2 çağrıları `PDFIUM_LOCK` ile sıralanır.
- **DOI ile zenginleştirme:** `ui_qml/importers.py::PdfImporter`, PDF'ten DOI okunduysa `PaperMetadataWorker` ile OpenAlex'ten yazar/yıl/dergi bilgisini tamamlar; başlık hâlâ dosya adıysa makale başlığıyla değiştirir (kullanıcının verdiği başlığa dokunmaz). Ağ yoksa sessiz kalır.
- **Web PDF indirme:** `download_remote` → `services/pdf_download_service.stream_fetch` (SSRF korumalı, `stream=True`) → `pdfkit/infra/downloader.py` akış halinde geçici dosyaya yazar; boyut sınırı (100 MB) **indirirken** ve `Content-Length` ile denetlenir, ilk bayt `%PDF-` olmalıdır, toplam süre 180 sn ile sınırlıdır.
- **Eski dosyaların benimsenmesi:** `PdfLibrary.adopt_legacy` (açılışta, `QmlBridge.run_startup_tasks`): eski düzendeki (kök dizinde `<8hex>_ad.pdf`) PDF'leri arka planda hash'leyip depoya alır, kaynakları (`url` veya `extra_metadata.local_pdf`) yeni dosyaya yönlendirir; 5'erli dilimlerle ana thread'i bloklamaz, tekrar çalıştırmak zararsızdır. Eski dosyayı `PdfStorageService.sweep_orphans` bir sonraki açılışta karantinaya alır.
- **Çöp toplama / karantina:** kaynak silinince `PdfFileManager.cleanup_local_pdf` depo dosyasını doğrudan silmez; `PdfLibrary.collect_garbage` hiçbir kaynağa bağlı olmayan belgeyi `pdfs/.trash/` altına taşır (30 gün sonra kalıcı silinir), kaydı olmayan eski depo dosyalarını da karantinaya alır. Windows'ta açık PDF kilitliyse 700 ms arayla 6 kez yeniden dener.
- **Tam metin:** `pdfkit.api.extract_page_texts` (pypdfium2; pypdf'ten ~15× hızlı, GIL'i bırakır). `ArticleExtractionService` sayfa numaralı HTML'i bununla üretir. Alıntı çapası indeksleri için **kullanılmaz** (Qt'nin PDFium'uyla indeksler birebir aynı olmayabilir).
- **Günlük DB anlık görüntüsü:** `utils/db_utils.snapshot_database_daily` (açılışta, günde bir; `pkm_app.db.daily-YYYYMMDD`, son 7).

## Alıntı alanı ve çapa çözümleyici (Faz 2)

- **Tablolar** (migration `d7e3b1a94c52`): `pdf_annotations` (alıntı), `pdf_page_notes` (sayfa noktası notu), `pdf_terms` (kelime). Hepsi `document_id`'ye bağlıdır (belge silinince CASCADE), kararlı ULID `uid` taşır (`pdfkit/domain/ids.py`; Obsidian blok kimliği ve derin bağlantı bunu kullanacak). Alıntıda anlam etiketi renkten ayrıdır: `label_key` (`important|finding|method|concept|critique|general`, `pdfkit/domain/labels.py`), isteğe bağlı `color`, serbest `tags` (JSON, `#` atılır, küçük harf).
- **Çapa (W3C TextQuote + TextPosition):** `quote_exact`, `quote_prefix`/`quote_suffix` (≤128 karakter) ve `segments` (JSON: `{page,start,end,text,polygons?}`; sayfa taşan seçim için şema hazır, arayüz v1'de tek parça üretir). Konum indeksleri **Qt PDFium** uzayındadır; `engine_fp` (`qtpdf-<Qt sürümü>`) üreten motoru kaydeder. `polygons` oluşturma anında `QPdfSelection.bounds()`'tan hazır gelir (`pdfkit/ui/pdf_text.py::segment_from_selection`), açılışta hesap gerekmez.
- **Çözümleyici** (`pdfkit/domain/anchoring.py`, saf Python): (1) kayıtlı konumdaki metin alıntıyla uyuşuyor mu (boşluk-normalize); (2) aynı sayfada normalize arama, birden çok eşleşmede önceki/sonraki bağlamla ve kayıtlı konuma yakınlıkla ayırma; (3) harf-rakam dışını yok sayan arama (satır sonu tirelemesi, ligatür boşlukları); (4) komşu sayfalar (±1); (5) bulunamazsa `orphaned`. 3 karakterden kısa alıntılar aranmaz (sahte eşleşme riski). Parçalı alıntıda her parça ayrı çözülür, biri bile bulunamazsa alıntı `orphaned` olur. Durumlar: `ok`, `pending_context`, `orphaned`, `unanchored`.
- **Servis** (`pdfkit/app/annotations.py::AnnotationService`): alıntı/not/kelime CRUD (commit/rollback burada), `relink` (yetim alıntıyı yeni seçime bağlar), `apply_resolution`, `backfill_context(document_id, provider, engine_fp)`: eski kayıtların konumunu doğrular, önceki/sonraki bağlamı çıkarır; belge ilk açıldığında `QtPageTextProvider` ile çağrılacak (Faz 3). Lone surrogate'lar `sanitize_text` ile `?` yapılır (indeksler kaymaz).
- **Eski veri köprüsü** (`pdfkit/app/legacy_import.py`, geçici): `highlights`/`pdf_notes`/`vocabulary` satırlarından PDF belgesine bağlı kaynakların kayıtları `legacy_id` ile kopyalanır; tekrar çalıştırmak güvenlidir ve eski tablodaki yorum/renk/silme değişikliklerini yansıtır, doğrudan pdfkit'te oluşturulan kayıtlara dokunmaz. Eski tablolar silinmez (arayüz Faz 3'e kadar onları kullanır); HTML makale alıntıları eski tabloda kalır. `PdfLibrary.start_maintenance` eski PDF benimsemesi bitince çalıştırır.

## Ölçümler ve kararlar

Spike sonuçları ve performans tabanı: `docs/plans/pdfkit-faz0-raporu.md` (pypdfium2 14–17× hızlı; seçimden gelen `bounds()` ile `getSelectionAtIndex` poligonları 643/643 birebir aynı → geometri oluşturma anında saklanabilir). Gerçek PDF'te mevcut `serialize` maliyeti alıntı başına ≈3,3 ms (hedef: Faz 3'te tek alıntı ekleme ≤16 ms).

## Sonraki fazlar

Faz 2 alıntı alanı ve çapa çözümleyici · Faz 3 UI veri akışı (artımlı model) · Faz 4 okuma deneyimi · Faz 5 Obsidian vault (klasörü kullanıcı uygulama içinden seçer) · Faz 6 kitaplık araması · Faz 7 sentez matrisi · Faz 8 eski kodun temizliği.

**İlgili sayfalar:** [[qml_arayuz]] · [[core_servisler]] · [[dizin_yapisi]] · [[log]]
