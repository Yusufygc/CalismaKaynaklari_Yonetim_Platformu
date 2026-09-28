# QML / QtQuick Arayüz Mimarisi

**Stack:** PySide6 QML (QtQuick 6, QtQuick.Controls, QtQuick.Layouts) · QAbstractListModel · Notion / Linear UI/UX

## Genel Bakış

Projenin mevcut QtWidgets arayüzüne paralel olarak, sıfırdan **Notion / Linear / Craft** tasarım dilinde akıcı, reaktif ve modern bir QML arayüzü kurulmuştur. Mevcut backend (Repository, Service, Controller, Alembic) katmanına dokunulmamış, Python ↔ QML köprüsü (`QmlBridge`) üzerinden tam entegrasyon sağlanmıştır.

Çalıştırma:
```bash
python main_qml.py
```
*(Mevcut QtWidgets arayüzü `python main.py` ile bağımsız olarak çalışmaya devam eder).*

---

## 1. Mimari Katmanlar

```text
[QML Arayüzü] (qml/)
  ├── main.qml               -> Ana pencere, Sidebar, Workspace, InspectorDrawer, Modal
  ├── theme/Theme.qml        -> Reaktif Singleton tema motoru (Dark/Light, renkler, tipografi)
  ├── components/            -> AppCard, AppButton, AppIconButton, AppBadge, AppSearchBar, InspectorDrawer, ResourceFormModal...
  └── views/                 -> ShowcaseView, ReaderView, KnowledgePoolView, SettingsView
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
