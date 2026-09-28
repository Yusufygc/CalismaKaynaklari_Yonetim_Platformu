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
│   └── extract_worker.py       # Makale tam metin çıkarma
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
│   └── vocabulary_repo.py
│
├── services/                   # İş mantığı ve doğrulama katmanı
│   ├── resource_service.py
│   ├── category_service.py
│   ├── tag_service.py
│   ├── highlight_service.py
│   ├── vocabulary_service.py
│   ├── scraper_service.py      # URL OpenGraph ve meta veri çekici
│   ├── article_extraction_service.py # Trafilatura ile zengin tam metin çıkarıcı
│   └── schemas.py              # Pydantic modelleri
│
├── controllers/                # UI-agnostik denetleyiciler (Hata yakalama, sinyal fırlatma)
│   ├── main_controller.py      # Facade controller
│   ├── resource_controller.py
│   ├── category_controller.py
│   ├── tag_controller.py
│   ├── highlight_controller.py
│   └── vocabulary_controller.py
│
├── ui_qml/                     # Python ↔ QML köprü katmanı
│   ├── bridge.py               # QmlBridge (State, filtreler, Q_PROPERTY/Slot'lar)
│   ├── image_provider.py       # IconImageProvider (qtawesome vektörel ikon sağlayıcı)
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
│   │   └── AppFilterChip.qml
│   └── views/                  # Sayfa görünümleri
│       ├── ShowcaseView.qml    # Bağlantı vitrini
│       ├── ReaderView.qml      # Dikkat dağıtmayan okuyucu
│       ├── KnowledgePoolView.qml # Bilgi havuzu (alıntılar/kelimeler)
│       └── SettingsView.qml    # Kategori ve etiket yönetimi
│
├── migrations/                 # Alembic veritabanı migrasyonları
└── tests/                      # Pytest test paketi
    ├── test_controllers/
    ├── test_qml/
    ├── test_repositories/
    ├── test_services/
    └── test_core/
```

---

## Katman Kuralları (Hard Rules)

1. **QML Katmanı (`qml/`):** Yalnızca görünüm ve kullanıcı etkileşimini yönetir. Doğrudan veritabanı veya servislere erişmez; tüm işlemler `bridge` (`QmlBridge`) nesnesi üzerinden yürütülür.
2. **Bridge Katmanı (`ui_qml/`):** QML'e Qt Property'leri, `QAbstractListModel` sanallaştırmasını ve Slot'ları sunar. İş mantığını `controllers/` katmanına delege eder.
3. **Controllers Katmanı (`controllers/`):** Kullanıcı girdisini doğrular, `services/` fonksiyonlarını çağırır, UI sınırında hataları yakalar ve `event_bus` sinyalleri fırlatır.
4. **Services Katmanı (`services/`):** İş mantığını barındırır. `session.commit()` ve `rollback()` yalnızca burada yönetilir.
5. **Repositories Katmanı (`repositories/`):** Yalnızca veritabanı sorgularını yürütür, iş mantığı içermez.
