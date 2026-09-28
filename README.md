# Kaynak Yönetim Platformu (PKM - Personal Knowledge Management)

Kaynak Yönetim Platformu, dijital varlıklarınızı (makaleler, videolar, web siteleri, notlar vb.) düzenlemek, takip etmek ve kolayca yönetmek için tasarlanmış modern bir masaüstü uygulamasıdır. İçeriklerinizi sadece depolamakla kalmaz, aynı zamanda estetik ve işlevsel bir arayüz ile tüketmenizi ve takip etmenizi sağlar.

---

##  Projenin Amacı

Bilgi çağında maruz kaldığımız yoğun içerik akışı, "sonra okurum/izlerim" diyerek kaydettiğimiz bağlantıların dijital bir yığında kaybolmasına neden olmaktadır. Bu projenin temel amacı;
- İnternetten topladığınız kaynakları yapılandırılmış bir şekilde saklamak,
- İlerleme durumunu (Okunmadı, Devam Ediyor, Tamamlandı) takip etmek,
- Görsel olarak zengin kart yapıları ile ilham verici bir çalışma ortamı sunmak,
- Clean Code ve SOLID prensiplerine sadık kalarak, genişletilebilir ve sağlam bir yazılım altyapısı sağlamaktır.

##  Temel Özellikler

- **Zengin URL Vitrini (URL Showcase):** Kayıtlı bağlantıları sıradan bir liste yerine asenkron olarak yüklenen web site görselleri (thumbnail) ile birlikte zengin kartlar (Rich Card) halinde sunar.
- **Kategorizasyon ve Etiketleme:** Kaynaklarınızı sınırsız hiyerarşik kategori ve renk kodlu etiketlerle (Tag) organize edebilirsiniz.
- **Detaylı Takip Sistemi:** Her kaynağın okunma/izlenme yüzdesini (%0 - %100) ve güncel durumunu takip edebilirsiniz.
- **Dinamik Tema Desteği:** Tek tıklama ile Açık (Light) ve Koyu (Dark) temalar arasında anında geçiş imkanı. QSS tabanlı, renk paleti ile senkronize çalışan modern bir arayüz sunar.
- **Otomatik Metadata Çıkarımı:** (Scraper Service) Eklenen bağlantılardan (URL) otomatik olarak başlık ve özet bilgilerini çeker.
- **Üç Panelli Modern Düzen (Three-Pane Layout):**
  - **Sol Menü (Sidebar):** Ana gezinme ve kategori/etiket filtreleme.
  - **Orta Liste:** Filtrelenmiş kaynak kartları veya URL vitrini.
  - **Sağ Detay Paneli:** Seçilen kaynağın tüm detaylarını görme ve hızlıca düzenleme (Resource Form/View).

---

##  Teknoloji Yığını (Tech Stack)

Uygulama, modern masaüstü teknolojileri ve standartları kullanılarak Python üzerinde inşa edilmiştir:

- **Arayüz Geliştirme (GUI):** PySide6 (Qt for Python)
- **Veritabanı (ORM):** SQLAlchemy 2.0
- **Veritabanı Motoru:** SQLite (Foreign Key kısıtlamaları aktif)
- **İkonlar:** QtAwesome (Dinamik renklendirme desteğiyle)
- **Stil Yönetimi:** Modüler `.qss` (Qt Style Sheets) dosyaları

---

##  Teknik Detaylar ve Mimari

Bu proje, büyük ölçekli ve kurumsal uygulamalara temel oluşturabilecek şekilde **Clean Architecture** prensipleri benimsenerek geliştirilmiştir.

### 1. Katmanlı Mimari
- **Models:** Veritabanı tablolarının (Category, Resource, Tag vb.) SQLAlchemy ORM sınıfları.
- **Repositories (Depo Katmanı):** Veritabanı işlemlerinin (CRUD) soyutlandığı katmandır. `BaseRepository` ile generic tip desteği sağlanarak tekrarlanan sorguların önüne geçilmiştir.
- **Services (Servis Katmanı):** İş mantığının (Business Logic) yer aldığı katmandır. Validation kuralları, veritabanı koordinasyonu ve dış servis (örneğin Web Scraper) entegrasyonları burada gerçekleşir.
- **UI (Kullanıcı Arayüzü):** Kullanıcı etkileşimlerini yönetir. UI bileşenleri veritabanına doğrudan asla erişemez; tüm işlemler Controller ve Servisler üzerinden yürütülür.

### 2. Event-Bus (Sinyal/Olay Mimarisi)
Proje içerisindeki veri akışı ve arayüz güncellemeleri, PySide6 tabanlı merkezi bir **Event Bus** (Olay Veriyolu) sistemi ile yönetilmektedir. Singleton bir yapıya sahip olan bu sistem sayesinde, farklı UI bileşenleri birbirine sıkı sıkıya bağlı kalmadan (loose coupling) haberleşebilir. Örneğin, bir kaynak güncellendiğinde tüm liste, detay paneli ve yan menü sayaçları otomatik olarak tepki verir.

### 3. Merkezi Varlık ve Stil Yönetimi
- **Sabitler:** String ifadeler, yazı tipleri (font), ikon adlandırmaları ve tema renk anahtarları `core/constants/` altında merkezi olarak yönetilir. Sihirli kelimeler (magic strings) engellenmiştir.
- **Dinamik QSS:** QSS dosyalarında doğrudan renk kodu yazmak yerine (`color: #fff;`), uygulama başlatıldığında veya tema değiştiğinde aktif temanın renk paletini okuyan özel değişkenler kullanılır. `resolve_theme_color` gibi yardımcı metotlarla tema değişimleri pürüzsüzce gerçekleştirilir.

### 4. Custom Painting (Özel Çizim)
Standart Qt widget'larının yetersiz kaldığı noktalarda `ui/components/painted.py` modülü altında `paintEvent` metotları ezilerek (override) özel UI çizimleri yapılmıştır (örn: ColorBadge, Avatar vb.).

---

##  Geliştirme Ortamı Kurulumu

Uygulamayı kendi ortamınızda çalıştırmak için aşağıdaki adımları izleyebilirsiniz.

### Ön Koşullar
- Python 3.10 veya üzeri
- Git

### Kurulum Adımları

1. **Repoyu Klonlayın:**
   ```bash
   git clone https://github.com/Yusufygc/Kaynak_Yonetim_Platformu.git
   cd Kaynak_Yonetim_Platformu
   ```

2. **Sanal Ortam (Virtual Environment) Oluşturun ve Aktif Edin:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Bağımlılıkları Yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Uygulamayı Başlatın:**
   ```bash
   python main.py
   ```

---

##  Gelecek Geliştirmeler (Roadmap)
- Tam zamanlı web senkronizasyonu ve mobil destek.
- Kaynaklar üzerinde zengin metin düzenleme (Rich Text Editor) ile not alma (Highlights & Notes).
- Markdown formatında içeri ve dışarı aktarma yetenekleri.

---

