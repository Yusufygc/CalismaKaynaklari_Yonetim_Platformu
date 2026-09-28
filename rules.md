# Proje: Kişisel Bilgi Yönetimi (PKM) - Kodlama ve Mimari Kuralları

Bu doküman, projenin geliştirilmesi sırasında uyulması gereken KESİN mimari ve kodlama standartlarını içerir. Tüm kod üretimleri bu kurallara tabi olmalıdır.

proje ortamı:C:\Users\ysfygc\anaconda3\envs\KaynakYonetim

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
her işlemden sonra ilgili wiki dosyası güncellecek.

## 7.Commit
yapılan işlmeler uygun ve detaylı açıklamalarla commit edilecek. Türkçe harflere dikkat et. ve claude code referansı verme.