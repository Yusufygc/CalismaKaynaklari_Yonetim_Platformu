# Wiki Değişiklik Kayıt Defteri

En yeni girdi her zaman en üstte olmalıdır.

---

## [2026-09-30] LINT | Wiki sağlığı: kırık linkler, rules.md konumu, log tipleri, .env.example

Denetim bulguları 11, 12, 18. Wiki lint: kırık link 7 → 0, öksüz sayfa 0. `[[tema_yonetimi]]`, `[[ui_layout]]`, `[[url_vitrin]]` hiç oluşturulmamış eski widget dönemi sayfalarıydı (ham kaynaklar git dışı `md/` altında, QSS/ThemeManager tasarımı — mevcut QML mimarisiyle çelişiyor); canlı sayfalarda `[[qml_arayuz]]`'a yönlendirildi, tarihsel `log.md` girdilerinde ham kaynak yolu olarak yazıldı. Kök `rules.md` → `docs/wiki/rules.md` (metodoloji §1.2; `index.md`'ye eklendi, eski conda yolu `.venv` ile değiştirildi). Log işlem tipi kuralı: yeni girdilerde `FEAT/FIX/REFACTOR/REVIEW/LINT/INGEST` (eski girdiler dokunulmadı) — `rules.md` ve `CLAUDE.md`'ye yazıldı. `CLAUDE.md` ortam bölümü `.venv` + `requirements.lock` + `.env.example`. Yeni `.env.example` (`APP_ENV`, `LOG_LEVEL`, `DATABASE_URL`, `LOG_FILE`, `DEFAULT_THEME`).

---

## [2026-09-30] FEAT | QML test güvenlik ağı (yükleme, bridge sözleşmesi, gerçek fare akışları)

Denetim bulgusu 8: 7.900 satırlık QML'in otomatik testi yoktu; son oturumdaki hataların (görünmeyen ikon, tıklanmayan "Tekrar dene", çift `anchors.topMargin`) hiçbiri `pytest`'e takılmadı. Yeni `tests/test_qml/test_qml_load.py`: her QML dosyası derlenir, `main.qml` gerçek bridge ile uyarısız açılır, QML'in kullandığı tüm `bridge.<üye>` / `Connections onXyz` adları `QmlBridge` meta-nesnesinde doğrulanır (bölme adımında kırılan çağrıları yakalayacak). Yeni `test_qml_flows.py` + `qml_harness.py`: QTest gerçek fare/klavye ile Market "Tekrar dene" (z-order regresyonu; `z: 1` kaldırılınca düştüğü doğrulandı), toplu seçim/kaydet, kayıtlı arama akışı, Bilgi Havuzu toplu silme + onay, Türkçe arama. `conftest.py`: `QT_QUICK_CONTROLS_STYLE=Basic`. `ArticleMarketView.qml`: `topicInput` objectName. 3 ardışık tam çalıştırma kararlı (394 test).

---

## [2026-09-30] FIX | UI thread'inde bloklayan IO arka plana alındı

`pdfOutline` (pypdf ile tüm PDF'i UI thread'inde parse ediyordu) → `PdfOutlineWorker` + `bridge.loadPdfOutline` / `pdfOutlines` property'si; `PdfSidePanel.qml` yüklenirken "Anahat yükleniyor...". `importLocalPdf` (büyük PDF'i UI thread'inde kopyalıyordu) → `PdfImportWorker`; artık `void` ve sonuç `pdfImportFinished(bool)` sinyaliyle gelir (`ResourceFormModal` sayaçla kapanır). `LibraryIndex` bridge'de önbelleklendi (`_reload_resources` geçersiz kılar; önceden her arama/kayıt/yenilemede tüm kaynaklar DB'den çekiliyordu); toplu Market kaydında kaynak olayları askıya alınıp tek yenileme yapılıyor (önceden kayıt başına tam yenileme). Gerçek thread havuzu ve gerçek QML ile doğrulandı (modal kapanıyor, anahat yükleniyor). Kapsam dışı: `QPdfDocument.load`. Denetim bulgusu 7. 360 test geçti.

---

## [2026-09-30] FIX | Tam metin liste sorgularında yüklenmiyor, okuma süresi tek kaynaktan

`Resource.full_text` artık `deferred=True` (PDF metinleri yüzlerce KB; vitrin/filtre sorguları hepsini belleğe çekiyordu, `data(ReadingMinutesRole)` her kart okunuşunda tam metni `split()` ediyordu). Yeni `resources.reading_minutes` sütunu (migration `e1f4a9c07b2d`, mevcut kayıtlar için geri dolumlu) + `utils/reading_time.py::estimate_reading_minutes` (tek kaynak, 200 kelime/dk); `ResourceService` `full_text`/`content` değişince yeniden hesaplar. `ResourceListModel`: kullanılmayan `FullTextRole` kaldırıldı, `ReadingMinutesRole` sütunu okur; `bridge._serialize_resource` aynı sütunu kullanır (eski tutarsızlık: liste 0, okuyucu 1 döndürüyordu; artık metin yoksa 0). Kullanılmayan `extra_metadata["reading_time"]` yolu kaldırıldı. Kullanıcı DB'sinin kopyasında doğrulandı (6 kaynak, migration + otomatik yedek). Denetim bulgusu 6. 350 test geçti.

---

## [2026-09-30] LINT | Ölü kod temizliği

Kaldırıldı (önce py/qml/test/wiki grep ile doğrulandı): 8 kullanılmayan `event_bus` UI sinyali, `QmlBridge.toggleSimpleMode` / `searchByAuthor`, `MarketFilters.is_empty`, `ResourceService.backfill_auto_categories`, `TagService.get_or_create_tag`, `ResourceListModel.get_resource_by_id` ve yalnızca bunları sınayan testler; `event_bus.md` güncellendi. **Bilinçli bırakıldı:** `updateCategory` / `updateTag` (backend var, SettingsView'da düzenleme arayüzü yok — silmek yerine eksik özellik olarak not edildi), `MainController.load_resource_pdf_notes` (facade Adım 13'te kalkacak), `requestPixmap`/`formatException` (Qt/logging override, false positive). Denetim bulgusu 13. 344 test geçti.

---

## [2026-09-30] FIX | Türkçe büyük/küçük harf ve diyakritik duyarsız arama

SQLite `ILIKE` yalnız ASCII katladığı için `İstanbul`/`ISPARTA`/`Şeker` aramada kaçıyordu (ölçüm: `LIKE` → 0). `utils/text_utils.fold_tr` + SQLite `fold_tr` fonksiyonu (`db_utils.register_sqlite_functions`) + `ResourceRepository._keyword_condition` (LIKE joker karakterleri literal). QML: `qml/js/text.js::foldTr`, `KnowledgePoolView` alıntı/kelime araması. Python↔JS eşitlik testi eklendi. Denetim bulgusu 4. 348 test geçti.

---

## [2026-09-30] FIX | Tarihler UTC yerine yerel saatle gösteriliyor

`utils/date_utils.py::format_local_datetime` (naive UTC → yerel saat dilimi; testlerde sabit `tz`). `bridge.py` (alıntı/kelime/kaynak `createdAt`) ve `ResourceListModel.CreatedAtRole` artık bunu kullanıyor; eski `format_date` (ölü) kaldırıldı. Denetim bulgusu 3: yerel 01:03 iken kartta "29.09.2026 21:58" görünüyordu (−3 sa). DB hâlâ UTC saklar, yalnızca gösterim değişti. 5 yeni test, 319 test geçti.

---

## [2026-09-30] FIX | Migration öncesi otomatik veritabanı yedeği

`utils/db_utils.py::init_db`: bekleyen migration ya da legacy DB varsa upgrade/stamp öncesi `pkm_app.db.bak-<zaman>-<revision>` yedeği (SQLite backup API), son 3 yedek tutulur; yeni/güncel DB için yedek yok. Denetim bulgusu 2 (yarım kalan migration kullanıcının tek veri kopyasını bozabilirdi). 6 yeni test (`test_db_backup.py`). 314 test geçti.

---

## [2026-09-30] FEAT | Bilgi Havuzu: alıntıları toplu seçip silme

Alıntı kartlarına seçim kutusu, listenin üstüne toplu seçim çubuğu (Tümünü seç / Seçimi temizle / Seçilenleri Sil (N)) ve onay penceresi eklendi. Backend: `HighlightService.delete_highlights` (tek commit, hata olursa geri alınır, olmayan/yinelenen kimlikler atlanır), `HighlightController.delete_highlights`, `MainController` facade, `QmlBridge.deleteHighlights` (tek yenileme, tek toast, açık okuyucu tazelenir). Etiket filtresi/arama/sekme değişince seçim bırakılır (görünmeyen alıntı yanlışlıkla silinmesin). Geçici DB ile QTest gerçek fare akışı doğrulandı (seç, tümünü seç, temizle, vazgeç, onayla). 308 test geçti.

---

## [2026-09-30] FIX | Makale Market: "Tekrar dene" butonu tıklanmıyordu

Boş/hata durumu `Column`ı, sonradan tanımlanan ve tüm alanı kaplayan `ResultsList` `ListView`ının altında kalıyor, tıklamalar ListView tarafından yutuluyordu ("Ara" butonu üst çubukta olduğu için çalışıyordu). `ArticleMarketView.qml`: `Column { z: 1 }`. QTest ile doğrulandı: `z` yokken tıklama 0 arama, `z: 1` ile yeniden arama çalışıp sonuç getiriyor. Aynı desen (kaplayan liste + üstte buton) diğer ekranlarda yok: ShowcaseView boş durumunda GridView görünmez, PdfReaderView hata `Column`ı sayfa alanından sonra tanımlı.

---

## [2026-09-30] FEAT | Makale Market: kayıtlı aramalar ve yeni yayın takibi (saved_searches tablosu)

Yeni `models/saved_search.py::SavedSearch` + Alembic `c4d9a6b1e2f3` (model↔migration farkı yok, downgrade/upgrade doğrulandı), `SavedSearchRepository`, `SavedSearchService`, `SavedSearchController` (+ `MainController` facade, `event_bus.saved_search_changed`), `workers/saved_search_worker.py`. `QmlBridge`: `saveSearch(topic, filters, tag)`, `runSavedSearch(id)` (form alanlarını `savedSearchApplied` ile doldurur, sonuçları "görüldü" işaretler, aramanın koleksiyon etiketini kaydedilen makalelere ekler), `deleteSavedSearch`, `checkSavedSearches()` (Market açılınca; son kontrolü 1 saatten eski aramalar; ağ hatasında sonraki açılışta yeniden denenir), `savedSearches`/`activeSavedSearchId`. `searchArticles` elle aramada kayıtlı arama bağlamını bırakır. QML: "Aramayı kaydet" popup, "Kayıtlı aramalar" çip çubuğu ("N yeni" rozeti, ✕ sil), koleksiyon etiketi ipucu. Geçici DB ile QTest gerçek fare akışı doğrulandı (yaz → Enter → kaydet → rozet → çalıştır → sil). 301 test geçti.

---

## [2026-09-30] FEAT | Makale Market: toplu seçim/kaydet, Sonra oku, BibTeX/CSV dışa aktarım

`PaperCard`: onay kutusu (kütüphanede olanda yok) ve "Sonra oku" butonu. `ArticleMarketView`: sonuç araç çubuğu — Tümünü seç / Seçimi temizle / seçili sayısı / BibTeX / CSV / "Seçilenleri Kaydet (N)"; seçim yeni aramada temizlenir, "daha fazla yükle"de korunur. `QmlBridge`: `saveMarketResults(list)` (tek yenileme, tek bildirim; kütüphanede olanlar ve aynı toplu işlemdeki tekrarlar atlanır — `LibraryIndex.add`), `saveMarketResultForLater` (`okuma-listesi` etiketi), `exportMarketResults(kind, fileUrl, papers)`; `saveMarketResult` ortak `_save_market_papers` üzerinden çalışır. Yeni `services/paper_export_service.py::PaperExportService`: BibTeX (`CitationService` yeniden kullanılır, çakışan anahtarlara a/b eki) ve CSV (Excel için `utf-8-sig`). `_write_export` uzantı/kodlama parametreli hale getirildi. Seçim yoksa dışa aktarım görünen tüm listeyi kapsar. Gerçek fare tıklamasıyla (QTest) onay kutusu/Tümünü seç/toplu kaydet doğrulandı. 283 test geçti.

---

## [2026-09-30] FEAT | Makale Market: keşif (referans/atıf/benzer/yazar) ve kütüphaneden okuma önerileri

`PaperMarketService.related_papers` artık `similar` (`related_to:`) ve `author` (`author.id:`) türlerini de destekler; `PaperResult.author_ids` (yazar adlarıyla aynı sırada), `referenced_work_ids`/`works_by_ids` toplu sorgular, `MarketFilters.author_id` (yalnızca yazar filtresiyle konu boş aranabilir). Yeni `services/reading_suggestion_service.py::ReadingSuggestionService` + `workers/reading_suggestion_worker.py`: kütüphane makalelerinin referanslarını sayıp kütüphanede olmayan ortak referansları (küçük kütüphanede eşik 1, ≥3 makalede 2) atıf sayısıyla sıralar; iki OpenAlex isteği yeter. Mevcut `RelatedPapersWorker` genelleştirildi (yeni worker yazılmadı). `QmlBridge`: `loadDiscovery(kind, openalexId)` + `marketDiscovery`, `searchByAuthor`, `loadLibrarySuggestions` + `marketSuggestions`, `resetMarketResults`; kütüphane rozeti bunlara da uygulanır. QML: yeni `PaperListItem.qml` (Kaynakça sekmesiyle ortak, DRY), `PaperCard` kartında Referanslar/Atıf yapanlar/Benzer açılır listesi ve tıklanabilir yazar adları, filtre çubuğunda yazar çipi ve "Kütüphaneden Öneriler" görünümü. Canlı OpenAlex ile doğrulandı (related_to, author.id, openalex OR filtresi, öneri). 272 test geçti.

---

## [2026-09-30] FEAT | Makale Market: zengin kart (PaperCard), kütüphanede tespiti, yinelenen kayıt engeli

`PaperResult.is_open_access/has_pdf` (OpenAlex `open_access.is_oa`, `primary_location.pdf_url`). Yeni `qml/components/PaperCard.qml`: dergi/DOI satırı, açık erişim + PDF rozetleri, açılır özet ("Devamını oku"), kütüphanede olan makalede "Kütüphanede" (pasif) butonu. Yeni `services/library_index.py::LibraryIndex` (DOI/OpenAlex kimliğiyle kütüphane eşleşmesi; `utils/doi_utils.py` normalize_doi/doi_from_url — bridge içindeki regex buraya taşındı). `QmlBridge`: sonuçlara `libraryResourceId` (0 = yok) yazılır (`_annotate_library`), `_reload_resources` sonunda `_refresh_library_flags` ile kayıt/silme sonrası Market ve Kaynakça sonuçları tazelenir; `saveMarketResult` aynı DOI/OpenAlex kaydı varsa eklemez ("zaten kütüphanende"). "Daha fazla yükle" listeyi yeniden atarken kaydırma konumu korunur. Okuyucu Kaynakça sekmesi de "Kütüphanede" gösterir. 252 test geçti.

---

## [2026-09-30] FEAT | Makale Market: filtre, sayfalama, hata/boş ayrımı, arama geçmişi

`PaperMarketService`: `MarketFilters` (yıl aralığı, açık erişim, tür, dil → OpenAlex `filter=`; `from_dict` QML değerlerini doğrular), `MarketPage(items, total, error)`, `search_page(topic, kind, filters, page)`. Ağ hatası artık boş liste olarak yutulmuyor, `MarketPage.error` ile taşınıyor. `MarketSearchWorker` filtre/sayfa/`request_id` alır (eski aramanın gecikmiş yanıtı atılır). `QmlBridge`: `searchArticles(topic, filters)`, `loadMoreArticles(kind)`, `marketMeta` (total/page/hasMore/error/loadingMore), `marketSearchHistory` (oturum boyunca, 10 kayıt, tekrarsız) + `clearMarketHistory`. `ArticleMarketView.qml`: filtre çubuğu, "Daha fazla yükle (n / toplam)", hata durumu + "Tekrar dene", son aramalar açılır listesi. Canlı OpenAlex doğrulandı (filtre + sayfa 2 + `language:tr`). Testler: yeni `test_paper_market_service.py`, worker/bridge testleri güncellendi (239 geçti).

---

## [2026-09-29] FIX | PDF okuyucu: sayfa sayacı kaydırmayı takip etmiyordu, başlık sağ butonlarla çakışıyordu

`PdfPageArea.qml`: geçerli sayfa yalnızca ScrollBar basılınca/pasifleşince güncelleniyordu (fare tekerleği/dokunmatik kaydırmada "1 / 15" sabit kalıyordu). Ortak `syncCurrentPage()` eklendi; `contentY` değişince 120 ms'lik `Timer` ile çağrılır (ScrollBar yolu da aynı fonksiyonu kullanır). `PdfReaderView.qml`: başlık genişliği sağ buton grubuna göre daralır (dar pencerede sayaçla üst üste biniyordu). Offscreen: contentY 1500/4200/9000 → sayfa 3/6/12, 0 → 1.

---

## [2026-09-29] FIX | Kaydırılan PDF sayfaları üst çubuğun üstüne taşıyordu

`PdfPageArea.qml` (`TableView`) ve `PdfReaderView.qml` gövde `Item`'ı `clip` etmiyordu; yukarı kaydırılan sayfalar üst çubuğu (geri/başlık/zoom butonları) kapatıyordu. İkisine `clip: true` eklendi; kaydırılmış halde offscreen render ile doğrulandı.

---

## [2026-09-29] FIX | 2./3. highlight'ta uygulama çökmesi (Instantiator + Shape.data.push)

**Kök neden:** `PdfPageArea.qml` kalıcı highlight'ları `Instantiator { delegate: ShapePath }` ile üretip `onObjectAdded: Shape.data.push(object)` ile Shape'e devrediyordu. Highlight eklenince `currentReaderResourceChanged` (model dizisi yenilenir) Instantiator'ın eski `ShapePath`'lerini yıkıyor, Shape ise sarkan işaretçi tutuyordu → `emit()` sırasında native segfault (kullanıcı 2./3. highlight'ta yaşadı; `python -X faulthandler` yığını `_refresh_reader_resource` gösterdi). **Yeniden üretim:** `QTest.mousePress/mouseMove/mouseRelease` ile gerçek sürükle-seç + swatch tıklama simülasyonu (offscreen) — düzeltmeden önce 2. highlight'ta segfault, sonra 30+ art arda highlight çökmesiz. **Düzeltme:** her highlight için ayrı `Shape` delegeli `Repeater` (manuel `data.push` yok). Kural: QML'de `Shape.data`'ya elle nesne ekleme; Repeater/Item delegate kullan. Önceki (asıl değil) şüpheliler — Qt bookmark modeli, `sendPostedEvents` — ayrıca giderilmişti.

---

## [2026-09-29] FIX | Boş DB ile açılıp sonradan eklenen kaynak kartlarının görünmemesi

`ShowcaseView.qml` boş-durum ve grid görünürlüğünü `bridge.resourcesModel.rowCount()`'a bağlıyordu; QML bu çağrıdan değişim bildirimi almadığı için binding bir kez (0 kayıtla) hesaplanıp donuyordu — temiz veritabanıyla başlayıp PDF yükleyince sayaçlar 1 gösterirken "kaynak yok" ekranı kalıyordu. `ResourceListModel`'e bildirimli `count` property'si (`countChanged`) eklendi, QML ona bağlandı (regresyon testi + boş başlayıp PDF ekleme senaryosu offscreen render ile doğrulandı). Ayrıca kartta yerel PDF adının depolama uuid öneki (`28a6fc4b_`) gizlendi (`format_display_url`). Genel kural: QML'de model boyutu için `rowCount()` değil bildirimli property kullan.

---

## [2026-09-29] FEAT | Kaynak ekle penceresine "Bilgisayardan PDF Yükle"

`ResourceFormModal.qml` (yeni kaynak modunda) URL alanının altına buton + çoklu seçimli `FileDialog` eklendi; seçilen her PDF mevcut `bridge.importLocalPdf` ile (sürükle-bırak ile aynı akış: depoya kopyala, `file://` kaynak, otomatik "Makale" kategorisi, tam metin çıkarımı) içe aktarılır. `importLocalPdf` artık başarıyı `bool` döndürür; en az bir dosya aktarıldıysa pencere kapanır. Yeni PDF mekanizması yok, sadece ikinci bir giriş noktası.

---

## [2026-09-29] FEAT | Akademik çalışma aracı: web-PDF native, arama/anahat/notlarım paneli, atıf, referans grafiği, dışa aktarım

Makale/PDF okuma mekanizması tez ve literatür taraması için genişletildi (ayrıntı: [[core_servisler]], [[qml_arayuz]], [[veritabani_semasi]]).

- **Web PDF native (D12):** `file://` dışındaki PDF URL'leri (`.pdf`, `arxiv.org/pdf/…`) artık `services/pdf_download_service.py` + `workers/pdf_download_worker.py` ile `pdf_storage_dir()`'a indirilip (SSRF korumalı `safe_http_get`, `%PDF-` imza doğrulaması, 100 MB sınırı) native okuyucuda açılıyor; yol `extra_metadata["local_pdf"]`'da. İndirme başarısızsa metin okuyucuya düşer. Bridge tek yerden karar verir: `_pdf_file_url(resource)`, `serialize` çıktısı `pdfFileUrl`/`pdfState`.
- **A (okuma verimliliği):** `PdfReaderView` — Ctrl+F metin arama (`PdfSearchModel`), yan panel `PdfSidePanel.qml` (Sayfalar küçük resimleri, Anahat/`PdfBookmarkModel`, Notlarım, Kaynakça). Highlight renkleri akademik anlama bağlandı (`core/constants/highlight_labels.py`: Önemli, Bulgu/Sonuç, Yöntem, Tanım/Kavram, Eleştiri/Soru — etiket renkten türetilir, DB kolonu yok). Highlight'a yorum: `highlights.comment` (migration `8b3f1c2d9a47`).
- **B (bilgi çıkarımı):** `services/citation_service.py` (APA/IEEE/BibTeX, `PaperInfoPopup.qml`'den kopyala), OpenAlex genişletmesi (`find_paper_strict`, `related_papers` → referanslar / atıf yapanlar; `PaperResult` artık doi/openalex_id/venue taşır ve `extra_metadata`'ya yazılır), `services/export_service.py` (kaynak/kütüphane Markdown: APA atıf + etikete göre gruplu alıntılar + yorum + sayfa notları + kelimeler), PDF'te seçilen kelime için cümle bağlamı (`utils/text_utils.py::extract_sentence`, `bridge.addPdfVocabulary`).
- **Altyapı düzeltmeleri:** Windows'ta QML `PdfDocument` dosyayı süreç bitene kadar kilitliyor (canlı doğrulandı) → silinemeyen PDF'ler için açılışta `services/pdf_storage_service.py::sweep_orphans`; silmede yeniden deneme. `QPdfDocument` cache'i kapatılırken gerçekten yok edilir. `_on_scrape_finished` artık `extra_metadata`'yı ezmez, birleştirir. Konsol: traceback yalnızca dosyaya (tek satır mesaj), `pypdf`/`trafilatura` gürültüsü dosyaya alındı, `fonttools` bağımlılığı eklendi.
- **Düzeltme (aynı gün, gerçek kullanım bulgusu):** Highlight/kelime seçiminde `PdfSelection.from/to` *ekran pikseli*, `QPdfDocument.getSelection()` ise *PDF noktası (pt)* bekler; zoom %100 değilken piksel gönderildiği için rastgele yer işaretleniyordu → QML'de `paper.pageScale`'e bölünüp gönderiliyor. Anahat: `PdfBookmarkModel`'in QML'e doğrudan bağlanması bozuk yer imli PDF'lerde (`qt.pdf.bookmarks: bookmark with invalid location and/or zoom …`, başlatılmamış bellek) çökme riski taşıdığı için `utils/pdf_outline.py::read_outline` (sayfa aralığı + sonlu koordinat doğrulaması) ile Python'da okunup düz liste olarak veriliyor. OpenAlex 502/503/504 geçici hatalarında bir kez yeniden deneme.
- **Çökme kök nedenleri (canlı segfault ile yeniden üretildi, `python -X faulthandler`):** (1) `_cleanup_local_pdf`'te `QCoreApplication.sendPostedEvents(None, DeferredDelete)` tüm Qt nesnelerinin ertelenmiş silmesini zorla çalıştırıp QML nesnelerini güvenli olmayan anda yok ediyordu → kaldırıldı, `deleteLater()` olay döngüsüne bırakıldı. (2) Anahat artık Qt `QPdfBookmarkModel` ile değil `pypdf` ile okunuyor ve dosya başına önbelleklenir (`ui_qml/bridge.py::pdfOutline`). (3) Okuyucu kapanınca `PdfDocument.source=""` "Cannot open" uyarısı basıyordu → son geçerli URL tutulur. Stres testi: art arda 20 highlight + sekme döngüsü + 12x aç/kapat + silme, çökme/uyarı yok.
- **Hata/log sistemi:** `event_bus.error_occurred` artık bridge'de toast'a bağlı (önceden hiçbir yer dinlemiyordu); controller'lar `log.exception`; bridge slot'ları dönüş değerini kontrol ediyor; `main.py` global `sys.excepthook` + kapanışta `waitForDone`.

Doğrulama: `pytest tests/` 220/220 yeşil. Gerçek PDF + gerçek OpenAlex/arXiv ile canlı e2e ve offscreen `grabWindow()` ile piksel doğrulaması yapıldı.

---

## [2026-09-29] FEAT | Native PDF okuyucu: sayfa render + highlight (düzenlenebilir) + satır notu

Şu ana kadar "PDF okuyucu" aslında `pypdf` ile metne çevrilmiş HTML gösteriyordu (çok sütunlu makalelerde metin sırası karışıyor, görsel/tablo kayboluyordu). Artık yerel (`file://`) PDF kaynaklar gerçek sayfa render'ıyla açılıyor, üstüne highlight (oluştur/renk değiştir/sil) ve nokta-bazlı margin notu eklendi. Üç fazda yapıldı, her fazdan sonra `pytest` + gerçek Qt engine ile canlı doğrulandı.

**Faz 1 — Native render**: Yeni `qml/components/PdfPageArea.qml`, Qt'nin `QtQuick.Pdf` modülündeki `PdfMultiPageView.qml`'i temel alan kopyala-değiştir bileşeni (Qt dokümantasyonu bunu resmen öneriyor). Yeni `qml/views/PdfReaderView.qml` (üst bar: geri, sayfa göstergesi, zoom, "Tarayıcıda Aç"). `bridge.openReader()` `resource.url` `file://...pdf` ise `currentView`'i `"pdfReader"` yapıyor, web'den PDF'ler (arXiv gibi) hâlâ eski metin-okuyucuda kalıyor (`QPdfDocument.source` ağdan indirme yapmıyor). Gerçek PDF ile doğrulandı: 15 sayfa, 612×792pt — doğru.

**Faz 2 — Highlight (oluştur + düzenle + sil)**: `highlights` tablosuna `start_index`/`length` kolonları eklendi (nullable, sadece PDF highlight'larında dolu; `page_number` da artık kullanılıyor). Kalıcılık **piksel değil karakter-index** bazlı — `QPdfDocument.getSelectionAtIndex(page, start_index, length)` ile zoom/scroll'dan bağımsız yeniden çiziliyor. `HighlightService.update_highlight_color` + `event_bus.highlight_updated` eklendi.

**Kritik keşif (canlı testte)**: QML script'inden `QPdfDocument.getSelection()`/`getSelectionAtIndex()` çağrılamıyor — `Unknown method return type: QPdfSelection` hatası. Çözüm: bu işlem tamamen Python'a (`ui_qml/bridge.py::addPdfHighlight`, `_load_pdf_document`, `_highlight_geometry`) taşındı — QML sadece seçimin `from`/`to` noktalarını yolluyor, geometri (`boundsPolygons`/`boundingRect`) `_serialize_resource()`'ta önceden hesaplanıp düz sayı listesi olarak QML'e gidiyor. Ayrıca `Repeater { delegate: ShapePath {...} }` de hata verdi (`ShapePath` bir `Item` değil) — `Instantiator` kullanıldı. Bir de gerçek off-by-one hatası bulundu: `length = endIndex - startIndex` (dikkat, +1 DEĞİL) — Python'da `QPdfDocument` ile izole test edilip doğrulandı.

**Faz 3 — Satır/Nokta Notu**: Yeni `models.PdfNote` (`page`, `x`, `y` — page-point uzayında, çözünürlükten bağımsız — `note_text`), `repositories/pdf_note_repo.py`/`services/pdf_note_service.py`/`controllers/pdf_note_controller.py` (Highlight üçlüsünün birebir kopyası). Üst barda "Not Ekle" toggle'ı; aktifken sayfaya tıklamak popover açıp `bridge.addPdfNote` çağırıyor. Notlar küçük bir ikonla (`fa5s.comment-alt`) o noktada kalıcı görünür, tıklayınca düzenle/sil popover'ı açılır. Bilgi Havuzu'na eklenmedi (sadece o kaynağın okuyucusunda yönetiliyor).

Doğrulama: `pytest tests/` 170/170 yeşil (12 yeni test). Gerçek bir PDF ile gerçek Qt QML engine üzerinden (offscreen) highlight + not birlikte render edilip **0 QML uyarısı/hatası** doğrulandı.

---

## [2026-09-28] FIX | Tooltip konumlandırma, sınır taşmaları ve ikon çakışmaları tamamen giderildi

Uygulama genelinde ve özellikle kenar çubuğu (Sidebar) ile vitrin üst çubuğundaki tooltip yerleşim ve çakışma sorunları çözüldü:

1. **Kenar Çubuğu İkon ve Logo Çakışmaları:**
   - **Kök Neden:** Daraltılmış menüdeki genişlet butonu (`>`) üst 100px alanında yer almasına rağmen tooltip'i yukarıya açarak doğrudan üstündeki yer imi (bookmark) logosunun üzerine biniyordu. Menüyü daralt butonunda (`<`) ise yatay hizalama ve pencere sınır hesaplamaları eksik olduğundan tooltip metni buton ikonunun üzerine çiziliyordu.
   - **Çözüm:** `AppIconButton.qml` içerisindeki dikey konumlandırma mantığı üst 100px eşiğine göre ayarlandı (`pt.y < 100` durumunda daima aşağı açılır). Ayrıca `tooltipPosition` özelliği genişletilerek (`"auto"`, `"bottom"`, `"top"`, `"left"`, `"right"`), `AppSidebar.qml` (`<` ve `>`), `ShowcaseView.qml` (görünüm seçici kapsül), `ReaderView.qml` (yazı boyutu/tarayıcı butonları), `InspectorDrawer.qml` (sabitle, favori, kapat butonları) ve `AppSearchBar.qml` (temizle butonu) bileşenlerinde `tooltipPosition: "bottom"` doğrudan açıkça tanımlandı.

2. **Yatay Pencere Sınırı Koruması (Boundary Clamping):**
   - **Kök Neden:** Sol veya sağ ekran kenarlarına çok yakın butonlarda (örn. 64px daraltılmış sidebar veya ekranın en sağındaki çekmece butonları), ortalanan tooltip pencerelerinin sol ya da sağ kenarından ekran dışına taşma ve kesilme riski bulunuyordu.
   - **Çözüm:** `AppIconButton.qml` içine `QtQuick.Window` desteğiyle reaktif yatay sınır koruma mantığı eklendi. Tooltip'in pencere içi koordinatı `[8px, Window.width - 8px]` aralığında dinamik olarak kilitlendi.

3. **Vitrin Üst Bar Yerleşimi (Anchor Mimarisi):**
   - Arama kutusu sola (`anchors.left`), sağ aksiyonlar (Görünüm seçici + Yeni Ekle) sağa (`anchors.right`) sabitlendi; kategori kaydırma alanı (`Flickable`) ise bu iki grubun arasına elastik olarak gerildi (`anchors.left: searchBar.right`, `anchors.right: rightActionsRow.left`).

Doğrulama: PySide6 görsel testleri (`verify_collapsed_dark.png`, `verify_daralt_dark.png`, `verify_daralt_light.png`, `verify_sade_dark.png`) ve `pytest tests/` 153/153 sıfır hata/uyarı ile doğrulandı.

---

## [2026-09-28] FEAT | Vitrin Sade Görünüm Modu (Kompakt Kartlar) eklendi

Kullanıcı tercihi doğrultusunda eski sistemdeki "Sade Mod" mekanizması modern QML mimarisine kazandırıldı:

- **Vitrin Üst Çubuğu Seçici:** `qml/views/ShowcaseView.qml` üst barına (kategori filtreleri ile Yeni Ekle butonu arasına) şık iki durumlu görünüm seçici kapsülü yerleştirildi (`fa5s.th-large` Zengin Görünüm, `fa5s.th-list` Sade Görünüm).
- **Format 1 (Kompakt Kartlar):**
  - `qml/components/AppCard.qml` bileşenine `isSimple` desteği getirildi. Sade modda 120px'lik büyük görsel/banner gizlenir; kartın soluna kategorinin renginde 3px dikey şerit eklenir; üst alanda kompakt kategori rozeti, domain ve pin/favori aksiyonları yer alır.
  - Kart yüksekliği 290px'den 136px'e, `GridView` hücre yüksekliği 305px'den 148px'e iner. Böylece ekrana tek bakışta iki kattan fazla kaynak sığar ve metin/not yoğunluğu artar.
- **Yalnızca Görsel Yoğunluk:** Filtre kısıtlaması olmadan tüm kaynaklar korunarak yalnızca görsel sunum ve kart kompaktlığı dinamik olarak değiştirilir.
- **Backend Durum Yönetimi:** `ui_qml/bridge.py` köprüsüne `isSimpleMode` özelliği, `isSimpleModeChanged` sinyali ve `toggleSimpleMode`/`setSimpleMode` slotları eklendi.

Doğrulama: `pytest tests/` 153/153 yeşil. `test_qml_bridge_theme_and_view_toggle` testine `isSimpleMode` ilk durumu ve slot/sinyal değişimleri dahil edildi.

---

## [2026-09-28] FIX | Durum filtreleri (DURUMLAR/Favoriler) ve Tooltip taşması düzeltildi

Kullanıcı arayüzünde tespit edilen iki kritik hata giderildi:

1. **Durum ve Favori Filtrelerinin Çalışmaması Düzeltildi:**
   - **Kök Neden:** `ui_qml/bridge.py::applyFilter` metodu filtre sözlüğünü `{"status": status, "is_favorite": favorite_only, "tag_id": tag_id}` anahtarlarıyla oluşturuyordu; fakat `services/resource_service.py::query_resources` metodu `filters.get("statuses")`, `filters.get("favorites_only")` ve `filters.get("tag_ids")` bekliyordu. Sonuç olarak SQL seviyesinde durum ve favori filtreleri tamamen yoksayılıyordu.
   - **QML Sinyal Uyumsuzluğu:** `AppSidebar.qml` içinde "Bağlantı Vitrini"ne tıklandığında durum ve favori filtre sıfırlama sinyali gönderilmiyordu; durum filtrelerine tıklandığında favori durumu sıfırlanmıyor, favorilere tıklandığında ise durum filtresi sıfırlanmıyordu. Bu da filtrelerin çapraz çakışmasına ve çift sorgu atılmasına yol açıyordu.
   - **Çözüm:**
     - `services/resource_service.py::query_resources` içine esnek takma ad (alias) ve skaler normalizasyon eklendi (`status`/`statuses`, `tag_id`/`tag_ids`, `priority`/`priorities`, `is_favorite`/`favorites_only` desteklenir).
     - `ui_qml/bridge.py::applyFilter` kanonik liste/anahtar formatına geçirildi (`statuses: [status] if status else None`, `favorites_only`, `tag_ids`).
     - `AppSidebar.qml` bileşenine atomik `filterSelected(string statusName, bool isFav)` sinyali eklendi ve tüm navigasyon butonlarında durum ile favori durumları eşzamanlı sıfırlanarak tek seferde `main.qml` üzerinden `ShowcaseView`'a iletildi.

2. **Tooltip Pencere Sınırı Taşması (Clipping) Düzeltildi:**
   - **Kök Neden:** `qml/components/AppIconButton.qml` içinde tooltip konumu sabit olarak `anchors.bottom: parent.top` idi. `ReaderView` üst okuma çubuğu veya üst bar gibi pencere tepe noktasına yakın (y < 50px) butonlarda tooltip pencere dışına taşıyor ve ekran görüntüsündeki gibi metnin üst yarısı kesiliyordu.
   - **Çözüm:** `AppIconButton.qml` içine akıllı konumlandırma (`tooltipPosition: "auto"`) eklendi. Butonun pencere içi konumu `mapToItem(null, 0, 0)` ile dinamik hesaplanarak:
     - Üst kenara 50px'den yakınsa tooltip otomatik olarak butonun **altına** (`anchors.top: parent.bottom`) açılır.
     - Sağ veya sol kenara taşma riski varsa `anchors.horizontalCenterOffset` ile pencere sınırları içinde kalacak şekilde otomatik kaydırılır.

Doğrulama: `pytest tests/` 153/153 yeşil (sıfır hata/uyarı). Hem backend alias'ları hem de bridge filtre akışı için yeni birim testleri eklendi (`test_query_resources_supports_scalar_and_alias_filter_keys`, `test_qml_bridge_apply_filter_status_and_favorites`).

---

## [2026-09-28] FEAT | Yerel PDF sürükle-bırak içe aktarma

Kullanıcı bilgisayarındaki bir PDF'i doğrudan pencereye sürükleyip bırakarak kaynak olarak ekleyebiliyor artık.

**Tasarım kararı:** İçe aktarılan PDF `core/paths.py::pdf_storage_dir()` (`%APPDATA%/PKM/pdfs/`) altına benzersiz adla **kopyalanır** (orijinal dosyaya dokunulmaz), `resources.url`'e standart bir `file:///...` URI'si (`Path.as_uri()`) yazılır. Bu sayede mevcut PDF/okuyucu altyapısının tamamı (`ExtractWorker`, "Tarayıcıda Aç" butonu, `ReaderView.qml`'in HTML render'ı) **hiç değişmeden** yeniden kullanıldı — sadece iki küçük dal eklendi:
- `ArticleExtractionService.extract_full_text()`: `url` şeması `file` ise ağ/SSRF mantığına hiç girmeden diskten okur (`_extract_local_pdf`, aynı `_extract_pdf_html` sayfa-numaralı HTML üreticisini kullanır).
- `utils/url_utils.py::format_display_url()`: `file://` URI'lerinde hostname yerine dosya adını gösterir (kart/okuyucu meta satırları otomatik düzelir, ek QML değişikliği gerekmedi).

**Yan bulgu — gerçek engel düzeltildi:** `services/resource_service.py::_validate_url`'in regex'i (`^https?://...`) `file://` URI'lerini reddediyordu (`InvalidURLError`) — canlı testte yakalandı. `file` şeması için host-format kontrolü atlanıp sadece boş-olmayan path yeterli sayılacak şekilde genişletildi; diğer geçersiz şemalar (örn. `ftp://`) hâlâ reddediliyor.

Yeni: `ui_qml/bridge.py::importLocalPdf(fileUrl)` slotu (kopyalama + kaynak oluşturma + arka plan extraction tetikleme, `saveMarketResult` ile aynı desen), `core/paths.py::pdf_storage_dir()`, `qml/main.qml`'de tüm pencereyi kaplayan `DropArea` + sürükleme sırasında görünen overlay, `ReaderView.qml`'de yerel PDF için kozmetik ikon/etiket düzeltmesi.

Doğrulama: `pytest tests/` 151/151 yeşil (6 yeni test). Gerçek bir arXiv PDF'i indirilip yerel dosya olarak sürükle-bırak akışından geçirildi — kopya doğru oluştu, orijinal dosya bozulmadı, arka plan extraction gerçek tam metni (15 sayfa, 40073 karakter) getirdi.

---

## [2026-09-28] FEAT | PDF tam metin desteği + Makale Market sayfası (QML)

**PDF desteği:** `ArticleExtractionService.extract_full_text()` artık URL doğrudan bir PDF'e işaret ediyorsa (`%PDF-` dosya imzası veya `.pdf` uzantısı) `pypdf` ile sayfa-numaralı HTML üretiyor (`<h3>Sayfa N</h3><p>...</p>`). İndirme tek, birleşik bir `requests`-tabanlı adıma (`core/net_utils.py::safe_http_get`, `ScraperService` ile paylaşılan) taşındı — önceden ayrı bir bulgu olan "trafilatura.fetch_url redirect'te SSRF'yi tekrar kontrol etmiyor" riski bu birleşmeyle kapandı. Gerçek arXiv PDF'iyle canlı doğrulandı (15 sayfa, 40073 karakter — önceden sadece HTML özet sayfası çekiliyordu). QML tarafında hiçbir değişiklik gerekmedi: `ReaderView.qml`'deki `TextEdit { textFormat: RichText }` zaten `<h3>/<p>` render ediyor.

**Makale Market sayfası (yeni):** Konu bazlı akademik makale keşfi. `services/paper_market_service.py::PaperMarketService` (OpenAlex Works API, ücretsiz) üç kategori döndürür: En Güncel / En Popüler / En Çok Atıf Alan. `workers/market_search_worker.py::MarketSearchWorker` arka planda çalıştırır, `ui_qml/bridge.py`'ye `searchArticles`/`saveMarketResult`/`marketResults`/`marketSearchLoading` eklendi. Yeni `qml/views/ArticleMarketView.qml` — arama sadece Enter/"Ara" ile tetiklenir (`AppSearchBar` bilinçli kullanılmadı, o her tuş vuruşunda sinyal fırlatıyor ve API rate-limitli — canlı testte 429 gözlendi). Sidebar'a yeni nav girişi (`qml/components/AppSidebar.qml`), `qml/main.qml`'e 5. sayfa eklendi.

**Yan bulgu — gerçek bug düzeltildi:** Canlı uçtan-uca testte `ui_qml/bridge.py::_on_resource_changed_event` çöktüğü görüldü — `event_bus.resource_added`/`resource_updated` `Signal(int)` (kaynak id'si) fırlatıyor ama handler bunu `Resource` nesnesi sanıp `.id`'ye erişiyordu (`AttributeError`). Qt bu istisnayı yutup logluyordu, state bozulmuyordu ama her kaynak ekleme/güncellemede sessizce `_update_selected_if_matches` çalışmıyor ve konsola hata basılıyordu. Parametre `resource_id: int` olacak şekilde düzeltildi (`_on_resource_deleted_event` ile tutarlı hale getirildi).

Doğrulama: `pytest tests/` 146/146 yeşil (5 yeni test: `MarketSearchWorker` başarı/hata, `searchArticles`/`saveMarketResult` bridge testleri). Gerçek OpenAlex + gerçek arXiv PDF ile uçtan uca canlı doğrulandı.

---

## [2026-09-28] REFACTOR | Mimari İhlaller, Tersine Bağımlılıklar ve Ölü Kodlar Temizlendi

Kapsamlı mimari denetim sonucunda tespit edilen katman ihlalleri, tersine bağımlılıklar, DRY ihlalleri ve ölü kodlar temizlendi:

- **Katman Ayrımı ve Tersine Bağımlılık:** `core/constants/status.py` dosyasındaki `from models import ResourceStatus` ters bağımlılığı giderildi; `ResourceStatus.label` özelliği ve `status_label` yardımcı fonksiyonu `models/resource.py` içerisine taşındı, `core/constants/status.py` kaldırıldı. `core` katmanının üst katmanlara bağımlılığı sıfırlandı.
- **UI & DB İzolasyonu:** `ui_qml/bridge.py` içindeki `Session` bağımlılığı ve ölü `ArticleExtractionService` importu temizlendi. `main.py` composition root olarak `MainController(session)` nesnesini üreterek `QmlBridge(controller=controller)` şeklinde enjekte etmeye başladı.
- **Thread & Worker Standartlaştırması:** `QmlBridge.scrapeUrl` içindeki ad-hoc `threading.Thread` ve doğrudan `ScraperService` çağrısı kaldırılarak `workers/scrape_worker.py` ve `QThreadPool` ile standartlaştırıldı; UI servis katmanından izole edildi.
- **DRY (Merkezi Güvenli HTTP İstemcisi):** `scraper_service.py` ve `article_extraction_service.py` içinde kopyalanmış olan SSRF korumalı redirect döngüsü `core/net_utils.py::safe_http_get()` olarak ortaklaştırıldı ve servisler bu merkezi fonksiyona bağlandı.
- **Tasarım Token'ları & Hardcoded Renkler:** QML bileşenlerinde (`main.qml`, `AppCard.qml`, `AppFilterChip.qml`, `AppIconButton.qml`, `AppButton.qml`, `AppSidebar.qml`, `ResourceFormModal.qml`, `ReaderView.qml`, `SettingsView.qml`, `ShowcaseView.qml`) yer alan tüm hardcoded HEX renkler `qml/theme/Theme.qml` içine eklenen yeni token'lara (`tooltipBg`, `overlayBg`, `backdropSubtle`, `chipUnselectedBg`, `badgeOverlay`, `gradientHeaderStart`, `fallbackCategoryColor`, `categoryPalette`) bağlandı. QML bileşen gövdelerinde hardcoded HEX sayısı sıfıra indirildi.
- **Merkezi Bildirim Metinleri:** `bridge.py` içindeki tüm ham Türkçe bildirim ve hata stringleri `core/constants/strings.py` (`AppStrings`) altına taşındı.
- **Ölü ve Yetim Kod Tasfiyesi:**
  - Projede kullanılmayan ve testi olmayan `services/paper_market_service.py` (OpenAlex servisi) silindi.
  - Eski QtWidgets QSS sisteminden kalan `core/constants/colors.py`, `core/themes/` (dark.py, light.py), `core/constants/fonts.py`, `core/constants/icons.py` modülleri silindi.
  - `ui_qml/models/resource_list_model.py` içindeki çağrılmayan `get_resource_dict_by_id()` silindi.
  - `core/config.py` Pydantic V2 `SettingsConfigDict` ile modernize edilerek tüm uyarılar (warnings) sıfırlandı.
- **Testler:** 141 testin 141'i de sıfır uyarı ile yeşil geçmektedir (`pytest`).

---

## [2026-09-28] REFACTOR | Worker'lar SOLID/SRP uyarınca workers/ paketine izole edildi

`core/workers.py` içinde birleştirilen arka plan iş parçacıkları ayrıştırılarak SOLID ilkelerine ve katman hiyerarşisine uygun hale getirildi:

- **SRP (Tek Sorumluluk Prensibi):** URL metadata taraması (`ScrapeWorker`) ve makale tam metin çıkarma (`ExtractWorker`) birbirinden tamamen bağımsız iki sorumluluk olduğundan, ayrı modüllere ayrıldı: `workers/scrape_worker.py` ve `workers/extract_worker.py`.
- **Katman Hiyerarşisi Temizliği:** `core/` temel katmanının üst `services/` katmanına (`ScraperService`, `ArticleExtractionService`) bağımlı olması mimari kural ihlali yaratıyordu. `workers/` kök paketi kurularak `core/` bağımsızlığı korundu ve `core/workers.py` silindi.
- **OCP (Açık/Kapalı Prensibi):** Gelecekte eklenecek yeni arka plan görevleri (örn. AI özetleme, PDF aktarımı) mevcut dosyayı değiştirmeden `workers/` altına yeni modül olarak eklenebilecek.
- **Testler:** `tests/test_workers/test_workers.py` eklenerek her iki worker mock servislerle test edildi. 141 testin tamamı geçmektedir.

---

## [2026-09-28] REFACTOR | Eski QtWidgets arayüzü kaldırıldı, QML tek ve ana arayüz yapıldı

Kullanıcı onayıyla eski QtWidgets arayüzü ve ilgili bağımlılıklar temizlendi:

- **Eski UI Dizinleri Temizlendi:** `ui/` dizini (QtWidgets views, components, layoutlar, qss enjeksiyonları) ve `assets/styles/` (.qss dosyaları) projeden tamamen silindi.
- **Controllers Katmanı Bağımsızlaştırıldı:** `ui/controllers/` altındaki iş mantığı köprüleri (`MainController`, `ResourceController`, `CategoryController`, `TagController`, `HighlightController`, `VocabularyController`) kök dizindeki bağımsız `controllers/` paketine taşındı.
- **Arka Plan Worker'ları Taşındı:** `_ScrapeWorker` ve `_ExtractWorker` `core/workers.py` içerisine taşındı.
- **Ana Giriş Noktası:** `main.py` doğrudan modern QML arayüzünü başlatacak şekilde güncellendi; `main_qml.py` kaldırıldı.
- **Testler:** Artık geçerli olmayan QtWidgets testleri temizlendi; `tests/test_qml/` altında `test_qml_bridge.py` ve `test_resource_list_model.py` ile QML altyapısı kapsama alındı. 139 testin tamamı geçmektedir.

---

## [2026-09-28] FEAT | QML ile modern Notion/Linear tarzı sıfırdan UI/UX mimarisi kuruldu

Mevcut backend, veritabanı ve test paketine dokunulmadan, paralel olarak modern bir QML/QtQuick arayüzü inşa edildi (`python main_qml.py`):

- **Tasarım Dili (Notion / Linear / Craft):** 1px ince zarif kenarlıklar, katmanlı yüzeyler (`bgBase`, `bgSidebar`, `bgSurface`, `bgElevated`), reaktif koyu/açık tema motoru (`Theme.qml` singleton).
- **Slide-over Inspector Drawer:** Sabit ve sıkışık sağ splitter yerine, karta tıklandığında sağdan pürüzsüz animasyonla kayarak açılan detay ve notlar çekmecesi (`InspectorDrawer.qml`).
- **Showcase (Vitrin):** `ResourceListModel` (`QAbstractListModel`) tabanlı 60 FPS akıcı kart ızgarası (`GridView`), küçük resim (thumbnail) / gradyan banner fallback'i, pin/favori mikro aksiyonları (`AppCard.qml`).
- **Dikkat Dağıtmayan Okuyucu (ReaderView):** 760px ortalanmış okuma sütunu, okuma ilerleme çubuğu, A-/A+ yazı boyutu kontrolleri, metin seçildiği anda imlecin üstünde beliren Kindle tarzı 5 renkli fosforlu alıntı ve kelime ekleme araç çubuğu.
- **Bilgi Havuzu & Ayarlar:** `KnowledgePoolView` (alıntı ve kelimeler) ve `SettingsView` (kategori renk paleti ve etiket yönetimi).
- **Python ↔ QML Köprüsü:** `QmlBridge` ve `IconImageProvider` (qtawesome ikonlarını `image://icon/...` üzerinden yüksek çözünürlüklü sunar).
- **Paralel Çalışma:** Eski QtWidgets yapısı (`python main.py`) korunarak `main_qml.py` bağımsız giriş noktası olarak eklendi. Test paketine `tests/test_qml/test_qml_bridge.py` eklendi; 160 testin tamamı geçmektedir.

---

## [2026-09-28] FEAT | Okuyucu sayfası sıfırdan tasarlandı

Okuyucu (`ReaderView`) düz metin gösteren tek bir `QTextEdit`'ten pratik/verimli bir okuma deneyimine yükseltildi:

- **Zengin HTML render:** `ArticleExtractionService.extract_full_text()` artık `trafilatura`'dan `output_format="html", include_formatting=True` ile gerçek başlık/paragraf/alıntı yapısı çeker (önceden düz metin). `QTextEdit.document().setDefaultStyleSheet(...)` ile tipografi (h1/h2/p/blockquote font-size, margin, line-height) uygulanır. Migration-öncesi düz-metin `full_text` kayıtları görüntüleme anında (`_looks_like_html` + `_plaintext_to_html`, ağ isteği yok) paragraflara sarılarak gösterilir — geriye dönük uyumlu.
- **Okuma sütunu:** ~760px genişlikte ortalanmış, okunur satır uzunluğu.
- **Meta şerit:** alan adı (`format_display_url` yeniden kullanıldı) + tahmini okuma süresi (kelime sayısı / 200 kelime-dk). Yazar/tarih bilinçli olarak dışarıda bırakıldı (trafilatura'da güvenilir gelmiyor).
- **Okuma ilerleme çubuğu** ve **scroll pozisyonu hatırlama** (oturum içi, kaynak bazlı, sadece bellekte — kalıcı değil).
- **Yazı tipi boyutu (A-/A+):** `QTextEdit.zoomIn()/zoomOut()`, oturum içi hatırlanır.
- **Highlight renk paleti:** seçim toolbar'ında tek "kaydet" butonu yerine `Colors.HIGHLIGHT_PALETTE`'ten (5 sabit fosforlu-kalem tonu) renk yuvarlakları — tek tıkla renkli alıntı.
- **Reader-içi alıntı silme:** render anında kurulan (kalıcı olmayan) id→pozisyon haritası ile imleç bir alıntının üstündeyken "Sil" butonu beliriyor; önceden sadece Bilgi Havuzu'ndan silinebiliyordu.

Backend (`HighlightService.create_highlight(color=...)`, `delete_highlight`) zaten hazırdı, değişiklik yok — iş tamamen UI katmanında. Şema/migration değişikliği yok. Kapsam dışı bırakılanlar: görsel/medya render (SSRF yüzeyini büyütmemek için), yazar/tarih metadata, kalıcı font-size/scroll tercihi, highlight offset kolonu (aynı metin tekrarında hâlâ sadece ilk eşleşme vurgulanıyor), içindekiler (TOC).

Doğrulama: `pytest tests/` yeşil (yeni `tests/test_components/test_reader_view.py` + güncellenmiş `test_article_extraction_service.py`), ayrıca offscreen smoke-test ile HTML render/legacy-wrap/highlight kaydet-sil akışları elle simüle edilip doğrulandı.

---

## [2026-09-28] REFACTOR | pkm_app/ klasörü kaldırıldı, kod kök dizine taşındı

`pkm_app/` ve repo kökü olmak üzere iki ayrı dizin kökü vardı: kod `pkm_app/` altında, wiki/CI/config kökte. Bu ayrım tek faydası olmayan bir katmandı ve `pkm_app/__init__.py`'de bare (`core.x`) ile qualified (`pkm_app.core.x`) import yollarını eşitleyen bir `sys.modules` aliasing hack'i gerektiriyordu — bu hack test suite'te iki farklı modül/singleton instance'ı oluşabilme riski taşıyordu (bkz. `test_main_controller.py`, `test_resource_flow.py` eski yorumları).

Yapılan değişiklik:
- `pkm_app/{assets,core,models,repositories,services,ui,utils,tests,migrations,main.py,alembic.ini}` → repo köküne taşındı (`git mv`).
- `pkm_app/__init__.py` (aliasing hack) ve onu doğrulayan `tests/test_package_imports.py` silindi.
- Tüm test dosyalarında `from pkm_app.X import ...` / `import pkm_app.X` / `monkeypatch.setattr("pkm_app.X...")` → `pkm_app.` öneki kaldırıldı (regex ile, ~20 dosya).
- `core/paths.py::_source_base()` ve `core/config.py::_ENV_FILE` derinlik hesapları yeni kök konuma göre doğrulandı/düzeltildi (`.env` artık `resource_path("..", ".env")` değil doğrudan `resource_path(".env")`).
- `.github/workflows/tests.yml`: `pytest pkm_app/tests/` → `pytest tests/`.
- `CLAUDE.md`, `README.md`: `python pkm_app/main.py` → `python main.py`, test komutları güncellendi.

Doğrulama: `pytest tests/` yeni kök konumdan tam suite yeşil.

---

## [2026-09-28] REVIEW | CI/CD eklendi (GitHub Actions)

Bulgu #10: 148 test var ama hicbir otomatik calistirma mekanizmasi yoktu — commit sonrasi kirilan bir test fark edilmeden birikebilirdi. `.github/workflows/tests.yml` eklendi: `push` (main) ve her `pull_request`'te `windows-latest` runner uzerinde `requirements.lock` + `pytest` kurup `pytest pkm_app/tests/` calistirir.

**Runner secimi:** `windows-latest` — proje CLAUDE.md'de Windows-only conda ortami (`C:\Users\ysfygc\anaconda3\envs\KaynakYonetim`) uzerinden tanimli, gelistirici gercek workflow'u budur. `ubuntu-latest` de teknik olarak calisabilir ama PySide6'nin offscreen platform plugin'i icin ek apt bagimliliklari (libegl1/libxkbcommon0 vb.) gerekebilir ve bu ortamda dogrulanamadi — spekulatif/dogrulanmamis Linux adimlarindan kacinildi (YAGNI).

**Dogrulama:** Workflow'daki komutlar (`pip install -r requirements.lock` + `pip install pytest` + `pytest pkm_app/tests/`, repo kokunden) tamamen izole, sifirdan bir venv'de (`.venv_ci_check`, sonradan silindi) birebir calistirilip 148 test yesil alindi — sadece dosya yazilip "calisir umuyorum" denmedi.

Detay: yok (proje-geneli altyapi, tek wiki sayfasina baglanmiyor).

---

## [2026-09-28] REVIEW | Uzun _build_ui metodlari alt-metodlara bolundu

Bulgu #9: 7 UI bilesen dosyasinda `_build_ui` (86-63 satir arasi) Long Method esigini asiyordu. Mekanik, davranis degistirmeyen refactor: her biri widget/section bazli alt-metodlara bolundu, hicbir attribute/sinyal/siralama degismedi.

- `resource_card.py`: `_build_top_row`/`_build_title`/`_build_description`/`_build_bottom_row` (77→4 metod, hepsi <30 satir)
- `url_rich_card.py`: `_build_thumbnail`/`_build_text_area`/`_build_bottom_row` (84→3 metod)
- `sidebar.py`: `_build_top_bar`/`_build_nav_list`/`_build_toggle_row` (tema+sade-mod satirlari ayni sekle sahip oldugu icin tek parametrik helper'dan kuruluyor — **dikkat:** ilk taslakta `_theme_layout`/`_simple_mode_layout` attribute'larini kaybediyordum (collapse/expand kodu bunlara `.setAlignment()` cagiriyor, grep ile yakalandi), helper'a `layout_attr` parametresi eklenerek duzeltildi). Ayrica `ToggleSwitch` importu method-ici lazy import'tan modul-seviyesine tasindi (donguysel bagimlilik yok, dogrulandi).
- `filter_bar.py`: `_build_category_filter`/`_build_tag_filter`/`_build_status_chips`/`_build_priority_chips`/`_build_favorite_chip`/`_build_clear_button` (66→6 metod, separator sayisi/sirasi birebir korundu)
- `resource_detail_panel.py`: `_build_header`/`_build_url_button`/`_build_status_row`/`_build_notes_area`/`_build_action_row`/`_build_delete_confirm_button` (63→6 metod)
- `resource_form.py`: `_build_category_field`/`_build_status_field`/`_build_priority_field`/`_build_content_field`/`_build_button_row` (86→5 metod)

**Bilinclii kapsam disi (`flow_layout.py::_do_layout`, 57 satir):** bolunmedi. Tek bir stateful geometri algoritmasi (`x`/`y`/`row_height`/`row_items` dongude birlikte tasiniyor); alt-metodlara bolmek bu mutable state'i parametre/return degeri olarak elden ele tasimayi gerektirirdi — okunabilirligi artirmaz, azaltir. Esigi sadece 7 satir asiyor, YAGNI/KISS geregi dokunulmadi.

**Dogrulama:** her dosyadan sonra `py_compile` + tam test suite (148 yesil sabit kaldi) + kritik olanlarda (sidebar collapse/expand, ResourceForm) ayrica offscreen smoke script; en sonda tum uygulama offscreen modda baslatilip sidebar/filter_bar/card zincirinden gecen bir sorgu calistirilarak crash olmadigi dogrulandi.

Detay: `md/ui_layout.md` (ham kaynak).

---

## [2026-09-28] REVIEW | Tema fallback'lerindeki hardcoded hex kaldirildi

Bulgu #8: `ui/components/toggle_switch.py` (`.get("accent_color", "#38BDF8")` vb. 3 yer) ve `color_picker_button.py` (`QColor("#3B82F6")` — QColorDialog baslangic rengi) `CLAUDE.md`'nin "no hardcoded colors" kuralini ihlal ediyordu. Ikisi de zaten projede var olan `ui/theme_utils.py::resolve_theme_color(theme_data, key)` helper'ina gecirildi (`theme_data` bossa/eksikse `Colors.THEMES["dark"][key]`'e duser — ayni fallback semantigi, artik merkezi). `color_picker_button.py`'deki sabit mavi, tema `accent_color`'una baglandi (artik tema degisiminde de tutarli).

**Regresyon kilidi:** `tests/test_ui_style_debt.py`'ye `test_ui_code_does_not_hardcode_hex_colors` eklendi (`ui/**/*.py` icinde `#RRGGBB` deseni arar) — `test_ui_code_has_no_inline_stylesheet_calls` ile ayni desen. 148 test yesil.

Detay: [[core_servisler]] · [[mimari_kurallari]].

---

## [2026-09-28] REVIEW | net_utils.py (SSRF guard) test kapsami eklendi

Bulgu #7: `core/net_utils.py::is_blocked_host` — projedeki en guvenlik-kritik fonksiyon — sadece scraper/extraction testleri uzerinden dolayli test ediliyordu, dedike testi yoktu. `tests/test_core/test_net_utils.py` eklendi (13 test): public IPv4/IPv6 izin veriliyor; loopback/private (RFC1918 10.x/172.16.x/192.168.x)/link-local (bulut metadata 169.254.169.254 dahil)/reserved/multicast/IPv6-loopback engelleniyor; **DNS rebinding senaryosu** (bir hostname birden fazla A kaydina cozumlenip biri bile ic ag ise engellenmeli) ayri test edildi; DNS cozumleme hatasi (`gaierror`) ve hostname'siz URL de engelleniyor. 147 test yesil.

Detay: [[core_servisler]].

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

Detay: `md/url_vitrin_layout.md` (ham kaynak) · [[core_servisler]].

---

## [2026-09-28] REVIEW | `except Exception` denetimi + MainController.delete_resource bug fix

Bulgu #4 (38x `except Exception`) tek tek okunarak değerlendirildi — grep sayımı yanıltıcıydı:

**Sonuç: 37/38 site kasıtlı, doğru pattern — bug değil.** Servis katmanındaki 20 site (`resource_service.py`, `tag_service.py`, `category_service.py`, `highlight_service.py`, `vocabulary_service.py`) tutarlı `try/commit → except Exception: rollback + log.exception + raise` deseni — DB commit'i çevreleyen bu geniş yakalama **kasıtlı**: hangi exception türü olursa olsun rollback garanti edilmeli, orijinal exception değişmeden yeniden fırlatılıyor (yutma yok). Daraltmak (`except ValidationError` gibi) yanlış olur — beklenmeyen bir DB hatasında (ör. disk dolu) rollback atlanır. `main_controller.py`'deki 16 site UI sınırı: servisten gelen her exception'ı yakalayıp `event_bus.error_occurred` ile arayüze bildiriyor — bu da kasıtlı, doğru. `resource_flow.py`'deki 2 site (`QRunnable.run()` içinde) arka plan thread güvenliği için aynı şekilde doğru. `resource_card.py`/`theme_utils.py`'deki 2 site qtawesome/SVG render fallback'i — defansif, doğru.

**Gerçek bulunan bug:** `MainController.delete_resource` diğer 12 yazma-metodunun (`add_resource`, `update_resource`, `toggle_pin`, `toggle_favorite`, `create_category`, ... vb.) hepsinde olan `event_bus.error_occurred.emit(str(exc))` çağrısını yapmıyordu — silme başarısız olduğunda kullanıcıya hiçbir geri bildirim gitmiyordu (loglanıyordu ama UI sessiz kalıyordu). Eklendi, `test_main_controller.py`'ye regresyon testi (`test_delete_resource_failure_emits_error`) eklendi.

**Yeni bulunan, henüz dokunulmamış risk (öncelik değerlendirmesi bekliyor):** `ui/components/url_rich_card.py::ThumbnailWorker` — `resource.extra_metadata["thumbnail"]` (scrape edilen sayfanın `og:image`'inden, yani saldırgan etkisindeki bir URL) `urllib.request` ile indiriliyor; `is_blocked_host` SSRF kontrolü **hiç çağrılmıyor** ve `ssl._create_unverified_context()` ile TLS sertifika doğrulaması **tamamen kapalı**. `scraper_service.py`'deki redirect açığından daha ciddi — burada baştan hiç SSRF koruması yok. Ayrı bulgu olarak kullanıcıya bildirildi.

Detay: [[core_servisler]] · `md/ui_layout.md` (ham kaynak).

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

Detay: [[veritabani_semasi]] · [[core_servisler]] · `md/ui_layout.md` (ham kaynak) · [[event_bus]] · [[veritabani_migrasyonlari]].

---

## [2026-07-06] FIX+STYLE | Dropdown ok ikonu eklendi + detay panelindeki URL şıklaştırıldı

**Dropdown ok ikonu (FIX):** `QComboBox`'a QSS uygulanınca (bu projede hepsine uygulanıyor) Qt native ok ikonunu tamamen kaybediyor — StatusCombo/FormCombo/FilterCombo hiçbirinde ok yoktu. `assets/icons/chevron_down.svg` (currentColor) eklendi; `theme_manager.py`'daki yeni `_write_themed_svg()` her tema uygulamasında bu SVG'yi o temanın `icon_color`'iyla boyayip `%APPDATA%/PKM/cache/combo_arrow.svg`'ye yaziyor, `base.qss::QComboBox::down-arrow` bu dosyayi `image: url(...)` ile referans veriyor (QSS dosya yolu ister, `load_theme_svg`'nin dondurdugu QIcon degil). Detay: `md/tema_yonetimi.md` (ham kaynak).

**URL gösterimi (STYLE):** `ResourceDetailPanel`'deki URL butonu artik ham/uzun URL yerine sadece alan adini (`utils/url_utils.py::format_display_url()`, örn. `github.com`) gösteriyor, tam URL tooltip'te duruyor; duz alt-cizili link yerine `OPEN_BROWSER` ikonlu bir chip/pill gorunumu aldi (`#DetailUrlButton` — `tag_badge_bg` arka plan, yuvarlak kenar, hover'da accent cerceve). Detay: `md/ui_layout.md` (ham kaynak).

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

Yapılanlar: `ResourceCard`'ın yanlış `simple=` parametresi geri alındı (her zaman tam render). `UrlShowcaseView` artık `_mode_stack` (rich/simple) taşıyor, `set_simple_mode(bool)` ile değiştiriliyor, kendi `SearchBar` + `InlineBanner`'ına sahip. `ContentWorkspace`'ten `ContentView` tamamen çıkarıldı; zaten tamamen ölü olduğu doğrulanan (`sidebar_filter_changed` sinyali sadece `"url_showcase"`/`"settings"` anahtarlarıyla tetikleniyordu) `_show_content`/`_show_favorites`/`_merged_filters_for_sidebar`/`_dispatch` dallı kodu silindi. Sidebar'dan "Tüm Kaynaklar" nav öğesi + ona ait ölü `AppStrings.ALL_RESOURCES`/`QtAwesomeIcons.ALL` sabitleri kaldırıldı. `ui/views/content_view.py` dosyası silindi. `UrlRichCard`'a dokunulmadı — hâlâ aktif olarak kullanılıyor (Sade Mod kapalıyken). Detay: `md/url_vitrin_layout.md` (ham kaynak), `md/ui_layout.md` (ham kaynak), [[event_bus]]. 87/87 test yeşil, offscreen smoke test ile mod geçişleri (rich↔simple), arama çubuğu, ekleme akışı ve banner'lar uçtan uca doğrulandı.

---

## [2026-07-03] PERF/TEMİZLİK | Kapsamlı debug denetimi: N+1 sorgu, gereksiz yenileme, ölü kod

İki paralel Explore ajanıyla tüm `pkm_app` taranıp bulgular manuel grep ile teyit edildi. Üç somut düzeltme yapıldı:
1. **Gereksiz üçlü yenileme:** `ResourceFlow._on_form_submitted`, `controller.add_resource`/`update_resource`'ın zaten `event_bus.resource_added`/`resource_updated` üzerinden senkron tetiklediği `workspace.refresh()`'i bir daha çağırıyordu — bu tekrarlı çağrı kaldırıldı (kaynak ekleme artık 1 gereksiz tam sorgu+kart-yeniden-kurulumu daha az yapıyor). Detay: `md/ui_layout.md` (ham kaynak).
2. **N+1 sorgu:** `ResourceRepository`'deki tüm sorgu metotları artık tek bir `_base_query()` helper'ından geçiyor (`joinedload(category)` + `selectinload(tags)`) — önceden kart render sırasında her kaynak için `.category`/`.tags` erişimi ayrı sorgu açıyordu. `status`/`category_id`/`is_favorite`/`is_pinned`/`url` kolonlarına yeni Alembic migration (`ff016ad9bf6e`) ile index eklendi — `query_filtered` tam bu kolonlarda filtreliyordu, önceden sadece PK indeksliydi. Migration geçici bir kopya DB üzerinde (`DATABASE_URL` env değişkeni ile) autogenerate edilip upgrade/downgrade döngüsüyle doğrulandı, gerçek DB'ye dokunulmadı. Detay: [[core_servisler]], [[veritabani_semasi]], [[veritabani_migrasyonlari]].
3. **Ölü kod temizliği:** Sıfır çağrısı/testi grep ile teyit edilen kod kaldırıldı — `MainController.load_all_resources/load_resources_by_filter/search_resources` (eski filtreleme yaklaşımı, `load_resources_with_filters` tarafından süperseslenmiş), `ResourceRepository.get_with_tags/get_pinned`, `ThemeManager.toggle_theme`, `ContentWorkspace.is_content_active`, `date_utils.format_datetime`, `icons.py::CustomIcons` sınıfı (+ satır 29'daki kopyala-yapıştır `SETTINGS` tekrarı) ve kullanılmayan `QtAwesomeIcons`/`AppStrings` sabitleri (`SEARCH`, `THEME_DARK/LIGHT`, `TAG`, `CATEGORIES`, `TAGS`, 6 adet `ERR_*` çeviri metni), birkaç kullanılmayan import (`theme_manager.py`, `filter_bar.py`, `url_rich_card.py`, `settings_view.py`), `.gitignore`'daki artık geçersiz `graphify-out` satırı. Bilinçli olarak dokunulmayanlar: `tag_service.get_or_create_tag` (test edilmiş servis katmanı public API'si), `core/constants/fonts.py` (CLAUDE.md'nin kanonik font kaynağı kuralı gereği scaffolding olarak korunuyor), `Colors.py`'deki kullanılmayan ~18 Python-taraflı isim takma adı (QSS hâlâ ham anahtarları kullanıyor). 87/87 test yeşil, offscreen smoke test ile refresh sayısındaki azalma ve eager-load sonrası kategori/etiket verisinin doğru render edildiği programatik doğrulandı.

---

## [2026-07-03] UI | Vitrinden kaynak ekleme + "Sade Mod" toggle eklendi

`UrlShowcaseView`'a `ContentView`'daki desenle birebir aynı bir "Yeni Ekle" butonu eklendi (`add_requested` sinyali `ContentWorkspace.add_requested`'e relay edilir); artık ana sayfa olan Vitrin'den başka sayfaya geçmeden kaynak eklenebiliyor. Ekleme akışı zaten sayfa-bağımsız çalıştığı için `ResourceFlow`/`MainController` katmanına dokunulmadı. Ayrıca sidebar'a tema-toggle'ın yanına ikinci bir `ToggleSwitch` — "Sade Mod" — eklendi (`event_bus.simple_mode_toggled(bool)`, yeni sinyal). Açıkken `ResourceCard` (Tüm Kaynaklar sayfası) durum rozeti, açıklama ve tarih/etiket satırını gizleyip sadece kategori ikonu + başlık + pin/favori gösteriyor; Vitrin sayfası (`UrlRichCard`) bu bayraktan etkilenmiyor. Kalıcılık eklenmedi — tema toggle'ı gibi oturum içinde bellekte tutuluyor, projede zaten hiçbir UI tercihi kalıcı değil (YAGNI). Detay: `md/ui_layout.md` (ham kaynak), `md/url_vitrin_layout.md` (ham kaynak), [[event_bus]]. 87/87 test yeşil, offscreen smoke test ile buton→form→kayıt→Vitrin yenileme zinciri ve sade mod açık/kapalı kart alanları programatik doğrulandı.

---

## [2026-07-02] UI | Katlanabilir Sidebar ve Özel Tema Geçiş Düğmesi (ToggleSwitch) Eklendi

Sidebar daraltılabilir (collapsed: 64px) ve genişletilebilir (expanded: 220px) hale getirildi. Hamburger menü ikonu (`assets/icons/hamburger.svg`) eklenerek sidebar üst kısmına konumlandırıldı. İkonun renginin temayla uyumlu değişmesi için `ui/theme_utils.py` dosyasına `load_theme_svg` eklendi, bu sayede SVG içindeki `currentColor` ifadesi aktif temanın ikon rengiyle dinamik olarak değiştirilmektedir. Geleneksel tema değiştirme butonu, pürüzsüz animasyonlu özel bir `ToggleSwitch` (`ui/components/toggle_switch.py`) bileşeniyle güncellendi. Ayrıca kullanıcının talebi doğrultusunda "Bağlantı Vitrini" (url_showcase) sayfası sidebar menü sıralamasında ilk sıraya getirildi. İlk açılışta hamburger menü ikonunun yüklenmeme sorunu Sidebar constructor'ında aktif tema çağrısıyla düzeltildi; başlangıç varsayılan teması 'light' olarak ayarlandı. Tema geçişlerinin yumuşatılması için `MainWindow` gövdesine 250ms'lik `QGraphicsOpacityEffect` fade-in animasyonu uygulandı. Detay: `md/tema_yonetimi.md` (ham kaynak), `md/ui_layout.md` (ham kaynak). 87/87 test yeşil ve programatik geçiş testleriyle doğrulandı.

---

## [2026-07-02] UI | Filtreleme çubuğu "yükseltilmiş navbar kartı" olarak yeniden tasarlandı

`FilterBar` (`ui/components/filter_bar.py`) artık gövdeden görsel olarak ayrık bir kart: kendi arka planı (`surface_elevated`), kenarlığı, 12px yuvarlak köşesi, `QGraphicsDropShadowEffect` gölgesi (tema değişince güncellenir). `QFrame` alt sınıfında QSS arka planının boyanması için gereken `WA_StyledBackground` attribute'u eklendi (önceden set edilmemişti, QSS'teki `background: transparent` olduğu için fark edilmiyordu). Filtre grupları arası `#FilterSeparator` ince ayraçlarla görsel olarak bölündü. Küçük UX iyileştirmesi: "Temizle" butonu hiçbir filtre aktif değilken otomatik devre dışı kalıyor. CSS-stili alfa'lı hex renkleri (`shadow_color` gibi) Qt formatına çeviren `_to_color` fonksiyonu `painted.py`'den `ui/theme_utils.py::to_qcolor()`'a taşındı (DRY, iki bileşen aynı dönüşümü paylaşıyor). Kullanıcıya 3 tasarım seçeneği (navbar kartı / popover menü / navbar+aktif filtre etiketleri) sunuldu, "Yükseltilmiş Navbar Kartı" seçildi. Detay: `md/ui_layout.md` (ham kaynak). 87/87 test yeşil, offscreen ekran görüntüsüyle dark/light tema ve aktif/pasif "Temizle" durumu görsel doğrulandı.

---

## [2026-07-02] FIX | Bağlantı Vitrini ana sayfa yapıldı, sayfa geçişi donması giderildi

Bağlantı Vitrini artık uygulamanın açılış sayfası (`main_window.py`, `Sidebar.select_by_key`). Kök nedeni bulunan donma hatası düzeltildi: `ContentWorkspace.apply_filter()` her geçişte iki `FilterBar.clear()` çağırıyordu, `clear()` sonunda senkron `filters_changed` fırlattığı için `refresh()` eski (henüz değişmemiş) sayfa index'iyle tetikleniyor, Vitrin'den ayrılırken tüm kartlar + ağ istekleri gereksiz yere 2 kez fazladan yeniden kuruluyordu. `FilterBar.clear(notify=False)` parametresiyle çözüldü. Ayrıca iki sessiz hata yutma noktası giderildi: `resource_flow.py`'deki `_ScrapeWorker.run()` artık istisnaları loglar (önceden worker sessizce ölüyordu), `url_rich_card.py`'deki `_on_thumbnail_loaded()` ağ/decode hatalarını `log.warning` ile loglar. Görsellerin DB'de doğru saklandığı (`extra_metadata.thumbnail`) ve `QNetworkAccessManager`+SSL'in ortamda çalıştığı ayrıca doğrulandı — "görseller hiç görünmüyor" şikayetinin ana kaynağı donma hatasıydı. Detay: `md/url_vitrin_layout.md` (ham kaynak). 87/87 test yeşil, offscreen smoke testiyle sayfa geçişi başına tam olarak 1 DB sorgusu yapıldığı doğrulandı (önceden fazladan tetikleniyordu).

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
