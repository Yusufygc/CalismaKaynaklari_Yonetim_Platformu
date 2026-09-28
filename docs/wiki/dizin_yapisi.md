# Dizin Yapısı ve Modül Haritası

**Kaynak (Raw Source):** `dizin_yapisi.md` (kök dizin)

Proje kök dizini `pkm_app/` altında çalışır. Yeni modül/sınıf oluştururken bu yapıya sadık kalınmalıdır.

**CI:** `.github/workflows/tests.yml` (repo kökü, `pkm_app/` dışında) — push/PR'da `pytest pkm_app/tests/` otomatik çalışır (2026-09-28).

```
pkm_app/
├── main.py                 # Giriş noktası (Entry point)
├── requirements.txt
├── .env.example
│
├── assets/
│   ├── icons/              # Özel SVG/PNG ikonlar
│   └── styles/             # Modüler .qss dosyaları
│
├── core/                   # Yapılandırma, sabitler, temel araçlar
│   ├── config.py
│   ├── logger.py
│   ├── exceptions.py
│   ├── events.py           # Event Bus singleton
│   ├── theme_manager.py    # Dinamik QSS enjeksiyonu
│   ├── themes/             # dark.py, light.py
│   └── constants/
│       ├── strings.py
│       ├── colors.py
│       ├── fonts.py
│       └── icons.py
│
├── models/                 # SQLAlchemy domain modelleri
│   ├── base.py
│   ├── category.py
│   ├── tag.py
│   └── resource.py
│
├── repositories/           # Veri erişim katmanı
│   ├── base_repository.py  # Generic CRUD
│   └── resource_repo.py    # Özelleşmiş sorgular
│
├── services/               # İş mantığı katmanı
│   ├── resource_service.py
│   └── scraper_service.py  # URL meta verisi çekme (gelecek faz)
│
├── ui/
│   ├── controllers/
│   │   ├── main_controller.py       (facade, delege eder)
│   │   ├── resource_controller.py
│   │   ├── category_controller.py
│   │   ├── tag_controller.py
│   │   ├── highlight_controller.py
│   │   ├── vocabulary_controller.py
│   │   └── resource_flow.py
│   ├── views/
│   │   ├── main_window.py
│   │   ├── grid_view.py
│   │   ├── detail_view.py
│   │   └── url_showcase_view.py
│   └── components/
│       ├── resource_card.py
│       ├── url_rich_card.py
│       ├── sidebar.py
│       └── search_bar.py
│
├── utils/
│   ├── date_utils.py
│   └── db_utils.py
│
└── tests/
    ├── test_models/
    ├── test_repositories/
    └── test_services/
```

## Katman Sorumlulukları
| Katman | Dizin | Görev |
|--------|-------|-------|
| Sunum | `ui/` | Sadece PySide6 kodu, iş mantığı içermez |
| Kontrol | `ui/controllers/` | Sinyal yakala, servisi çağır |
| İş Mantığı | `services/` | Validation, iş kuralları |
| Veri Erişim | `repositories/` | SQLAlchemy sorguları |
| Domain | `models/` | Tablo tanımları |

## İlgili Sayfalar
[[mimari_kurallari]] · [[core_servisler]] · [[veritabani_semasi]] · [[ui_layout]]
