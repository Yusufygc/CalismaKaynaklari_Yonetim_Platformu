# Proje: Kişisel Bilgi Yönetimi (PKM) - Kodlama ve Mimari Kuralları

Bu doküman, projenin geliştirilmesi sırasında uyulması gereken KESİN mimari ve kodlama standartlarını içerir. Tüm kod üretimleri bu kurallara tabi olmalıdır.

Proje ortamı: proje kökündeki `.venv` (Python 3.10; `python -m venv .venv`, `pip install -r requirements.lock`). Çalıştırma: `.venv\Scripts\python.exe main.py`; test: `.venv\Scripts\python.exe -m pytest tests`.

## 1. Yazılım Prensipleri (Software Principles)
- **SOLID:** Tüm sınıflar Tek Sorumluluk (Single Responsibility) ilkesine uymalıdır. Sınıflar genişlemeye açık, değişime kapalı (Open/Closed) olmalıdır. Bağımlılıkların tersine çevrilmesi (Dependency Inversion) için arayüzler/soyut sınıflar (ABC) kullanılacaktır.
- **Clean Code:** Değişken ve fonksiyon isimleri kendi kendini açıklayıcı (self-documenting) olmalıdır. `process_data()` gibi belirsiz isimler yerine `extract_metadata_from_url()` gibi net isimler kullanılmalıdır. Yorum satırları sadece "Neden?" sorusunu cevaplamak için kullanılmalı, "Nasıl?" sorusunu zaten kodun kendisi anlatmalıdır.
- **DRY (Don't Repeat Yourself):** Tekrar eden hiçbir mantık yazılmamalıdır. Ortak fonksiyonlar `utils/` veya `helpers/` dizinlerine taşınmalıdır.
- **Teknik Borç (Technical Debt):** "Şimdilik çalışsın, sonra düzeltiriz" (Hack) yaklaşımları KESİNLİKLE YASAKTIR. Her modül yazıldığında test edilebilir ve izole olmalıdır.

## 2. Merkezi Varlık ve Tema Yönetimi (Central Asset Management)
Tüm UI bileşenleri hard-coded değerler yerine aşağıdaki merkezi dosyalardan beslenmelidir:
- **Stringler:** `core/constants/strings.py` (`AppStrings` — Gelecekte i18n desteği için tüm metinler ve bildirimler buradan çekilecek).
- **Tasarım Token'ları (Renkler, Fontlar, Radius, Boşluklar):** `qml/theme/Theme.qml` (Singleton QML nesnesi; reaktif dark/light tema yönetimi).
- **İkonlar:** Standart ikonlar için `qtawesome` kütüphanesi (`image://icon/<name>/<hex>` şemasıyla `IconImageProvider` üzerinden). Özel ikonlar `assets/icons/` klasöründe SVG formatında tutulur.

## 3. Stil ve Görünüm Yönetimi (QML & Theme)
- Bileşen gövdelerinde ad-hoc / hardcoded HEX renk kullanımı KESİNLİKLE YASAKTIR (`Theme.*` token'ları kullanılır).
- Notion / Linear / Craft minimalist tasarım dili uygulanır.
- Tüm görsel katmanlar (bgBase, bgSidebar, bgSurface, bgElevated, borderSubtle, borderStrong, accent vb.) `Theme.qml` üzerinden dinamik ve reaktif olarak yönetilir.

## 4. Mimari Desenler (Design Patterns)
- **Model-View-Controller (MVC) / Model-View-Presenter (MVP):** UI (View) veritabanı veya iş mantığını (Model) doğrudan ÇAĞIRAMAZ. İletişim her zaman Controller/Presenter veya Servis katmanı üzerinden olmalıdır.
- **Repository Pattern:** Veritabanı sorguları (SQLAlchemy) UI veya Servis koduna karışmamalı, `repositories/` klasörü altındaki sınıflarda (Örn: `ResourceRepository`) izole edilmelidir.
- **Dependency Injection:** Servisler veya UI bileşenleri, ihtiyaç duydukları veritabanı oturumlarını (session) veya bağımlılıkları constructor (`__init__`) üzerinden dışarıdan almalıdır.
- **Event-Driven UI:** Arayüz güncellemeleri için doğrudan metod çağırmak yerine PySide6 `Signal` ve `Slot` yapısı kullanılmalıdır.

## 5. Konfigürasyon, Hata ve Log Yönetimi
- **Konfigürasyon:** Uygulama ayarları (DB yolu, ortam değişkenleri) `core/config.py` üzerinden yönetilecektir (Pydantic BaseSettings veya standart `os.environ` tercih edilebilir).
- **Hata Yönetimi:** Kaba `Exception` yakalamak yerine `core/exceptions.py` içinde tanımlanmış projeye özel özel hata sınıfları (Custom Exceptions) kullanılmalıdır. (Örn: `raise InvalidURLError("URL formatı hatalı")`).
- **Loglama:** Sadece konsola print atmak yasaktır. `core/logger.py` üzerinden yapılandırılmış, hem dosyaya (app.log) hem konsola yazan standart `logging` modülü kullanılmalıdır.

## 6. Wiki dosyaları güncellemesi
Her işlemden sonra ilgili wiki dosyası güncellenir ve `docs/wiki/log.md`'nin **en üstüne** `## [YYYY-AA-GG] İŞLEM_TİPİ | Kısa açıklama` girdisi eklenir.

**İzinli işlem tipleri:** `FEAT` (yeni özellik), `FIX` (hata düzeltme), `REFACTOR` (davranış değiştirmeyen yeniden düzenleme), `REVIEW` (kod/mimari inceleme), `LINT` (bakım, ölü kod, wiki sağlığı), `INGEST` (dış kaynak/doküman alma). Eski girdilerdeki tipler (BUILD, UI, PERF, ...) olduğu gibi bırakılır; yeni girdiler bu altı tipten birini kullanır.

## 7. Tekrarlanmaması Gereken Hatalar (Denetimden Çıkan Dersler)
Aşağıdaki maddeler gerçekten yaşanmış hatalardan çıkarıldı; kod yazarken/incelerken kontrol listesi olarak kullanılır.

**Boyut ve karmaşıklık eşikleri** (denetim betiği `audit_metrics.py` ile ölçülür; aşılırsa bölmeden merge edilmez)
- Dosya ≤ 500 satır; sınıf ≤ 300 satır ve ≤ 20 metot (property getter ve slot dahil); fonksiyon ≤ 50 satır; CC ≤ 10; parametre ≤ 5; import ≤ 25; QML dosyası ≤ 500 satır.
- Bir sınıfın API yüzeyi (QML slot/property) tek başına 20'yi aşıyorsa yardımcı sınıf yetmez: alt-bridge'e böl (`library / reader / annotations / citations / market / discovery / searches / settings`). Mantığı `ResourceFormHandler`, `MarketSaver`, `LibraryEventRouter` gibi yardımcı sınıflara taşı.
- Tek dosyada büyüyen "tanrı sınıf" (eski `QmlBridge` 1.737 satır / 131 metot) yeniden oluşmasın: yeni özellik ilgili alt-bridge'e girer, kök `QmlBridge` yalnızca kabuktur.
- 8+ parametre yerine küçük veri sınıfı (`ResourceFilter`, `HighlightPosition`) veya `QVariantMap` (`selection`) kullan.

**Katman ve bağımlılık**
- Alt-bridge'ler birbirini serbestçe çağırmaz; değişiklikler `event_bus` üzerinden akar. Zorunlu eş bağımlılık constructor DI ile ve dar bir yüzeyle olur (`start_search`, `refresh_if_open`). İki bridge aynı durumu paylaşacaksa ortak durum nesnesi kullan (`SavedSearchState`), karşılıklı çağrı yapma.
- `event_bus`'a lambda ile değil, QObject'e bağlı metotla bağlan (yoksa test/yeniden oluşturmada eski bridge'ler olay dinlemeye devam eder). Olay işleyicileri ayrı QObject çocuğu olabilir (`LibraryEventRouter`).
- Kullanılmayan "proxy" metot ekleme (`ResourceService.get_by_status` vb. hiç çağrılmıyordu); eklemeden önce çağıranı olduğunu doğrula, ölü kodu sil.
- `commit()`/`rollback()` yalnızca Service katmanında.

**QML**
- Yeni QML üyesi eklerken `bridge.<alt>.<üye>` yolunu kullan; kök `bridge`'e iş alanı üyesi ekleme. Sözleşme testi (`test_qml_load.py`) `bridge.<alt>.<üye>` ve `Connections onXyz` varlığını doğrular — üye yeniden adlandırılınca QML de güncellenmelidir.
- Ekranı kaplayan ListView/TableView kardeşi tıklamayı yutar: hata/boş durum katmanlarına `z: 1` ver ("Tekrar dene" hatası).
- Property adı kapsamdaki `id` ile aynı olmasın (`selection: selection` bağlama döngüsü).
- `.pragma library` JS `bridge` context property'sini göremez; gereken değerleri parametre olarak geçir.
- Genel `Shortcut { sequence: "Esc" }` metin alanındaki `Keys.onEscapePressed`'ı yutar: düzenleme alanlarına `Keys.onShortcutOverride: (event) => event.accepted = (event.key === Qt.Key_Escape)` ekle.
- Aynı dokunuşta birden fazla `TapHandler` çalışır: "dışarı tıkla kapat" işleyicisi, aynı dokunuşta açılan popover'ı kapatmamalı (popover açılış sayacı `openCount` deseni).
- 500 satırı aşan QML'i bileşenlere böl; alt bileşen durumu `property` ile alır, eylemi sinyalle döner, kök `id`'ye dokunmaz. Yıkıcı işlemler için ortak `ConfirmDialog`, renk seçimi için `ColorPalette` kullan (tekrar yazma).
- `Column`/`Row` `padding` kullanıyorsan çocuk genişliğinden padding'i düş (`parent.width - parent.leftPadding - parent.rightPadding`); yoksa metin sağdan taşıp kırpılır (Vitrin kartı hatası).
- Yeniden atanan listelerde (`model:` yeniden bağlanınca ListView başa sarar) konumu koru; yalnız yeni aramada başa dön (Market kaydetme hatası).
- Test edilecek öğelere `objectName` ver; TableView delegate'leri QObject ağacında değildir, `findChild` yerine görsel ağaç (`qml_harness.walk/find_named`) kullan.

**Veri, arama ve tarih**
- Kullanıcıya gösterilen tarihler UTC → yerel saat (`utils/date_utils.format_local_datetime`); `strftime`'ı ham UTC üzerinde çağırma.
- Türkçe arama harf/diyakritik duyarsız olmalı (`fold_tr`; SQLite fonksiyonu + `qml/js/text.js` aynı kuralı uygular, test ile eşlenir). `lower()` / `ILIKE` tek başına yetmez.
- LIKE joker karakterleri (`% _ \`) kullanıcı girdisinde kaçırılır.
- Dış kimlikler (OpenAlex `W…/A…`, DOI) filtre/URL'ye girmeden regex ile doğrulanır (filtre enjeksiyonu). Bir servis yalnız DOI ile bulamazsa sessizce yanlış kayıt döndürme: yedek arama yalnız kesin (başlık birebir) eşleşmede kabul edilir.
- Büyük metin sütunları (`full_text`) `deferred` yüklenir; liste sorguları onu seçmez. Türetilmiş değer (okuma süresi) sütunda tek kaynaktan yazılır.
- Migration öncesi DB yedeği alınır (`init_db`); yedek olmadan şema değiştirme.

**UI thread ve IO**
- UI thread'inde dosya kopyalama, PDF anahat okuma, ağ isteği yapılmaz; worker (`QRunnable` + Signals) kullan. İstisna gerekiyorsa (`QPdfDocument.load`, QObject thread affinity) önce ölç ve gerekçeyi kodda/wiki'de belgele.
- Arka plan sonucu geç gelebilir: istek kimliği/anahtar karşılaştırıp bayat yanıtı at (`request_id`, `openalex_id`).
- Windows'ta açık PDF dosyası kilitlenir: silmeden önce `QPdfDocument.close()` ve yeniden deneme.

**Test ve doğrulama**
- Gerçek kullanıcı DB'sine dokunma; geçici/in-memory DB kullan. Kalıcı `skip` bırakma; gerçek dosya gerektiren testler için üretilmiş deterministik PDF (`tests/pdf_factory.py`).
- QML değişikliğinde yalnız derleme yetmez: gerçek fare/klavye akışı (QTest, offscreen) yaz; hata düzeltmesinde düzeltmeyi geri alınca testin düştüğünü doğrula (mutasyon).
- Bölme/taşıma refaktöründe önce güvenlik ağı (QML yükleme + sözleşme testi), sonra ekran görüntüsü öncesi/sonrası piksel karşılaştırması.
- CI: `pytest --cov --cov-fail-under=84` ve `pip-audit`; bağımlılık eklerken `requirements.txt` (doğrudan) + `requirements.lock` (tam, `scripts/make_lock.py`) birlikte güncellenir, kullanılmayan bağımlılık bırakılmaz.

**Süreç**
- Denetimde çıkan kalıp: değişiklikler commit'lenmeden birikti (93+ commit'siz dosya). Mantıksal parçalarda, düzenli commit at.
- Çok satırlı düzenlemelerde kabuk tırnak/kesme işareti hatası çıkar: betiği dosyaya yaz. CRLF dosyalarda (`log.md`) `sed -i` kullanma; satır sonunu koruyan yardımcı kullan.
- Wiki'de kalıntı referans bırakma: silinen/yeniden adlandırılan üye için `docs/wiki` taranır, kırık link 0 olmalı.

## 8. Commit
yapılan işlmeler uygun ve detaylı açıklamalarla commit edilecek. Türkçe harflere dikkat et. ve claude code referansı verme.

---

**İlgili sayfalar:** [[mimari_kurallari]] · [[index]] · [[log]]
