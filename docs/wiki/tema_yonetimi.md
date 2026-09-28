# Dinamik Tema Yönetimi

**Kaynak (Raw Source):** `tema_yonetimi.md` (kök dizin)

## Yaklaşım: Dinamik QSS Enjeksiyonu
- QSS dosyalarında `#FFFFFF` gibi hard-coded HEX **yasaktır**.
- Bunun yerine `{{ bg_primary }}` şablonu kullanılır; `ThemeManager` çalışma anında doldurur.
- Dosyalar: `core/theme_manager.py` + `core/themes/dark.py`, `light.py`

## Tema Veri Yapısı
Her tema Python sözlüğü:

| Anahtar | Açıklama |
|---------|----------|
| `bg_primary` | Ana arka plan |
| `bg_secondary` | Kart/panel arka planı |
| `text_primary` | Ana metin |
| `text_secondary` | Alt başlık, tarih |
| `accent_color` | Buton, aktif menü |
| `border_color` | Çizgi, ayırıcı |
| `icon_color` | qtawesome ikon rengi |
| `on_accent` | Accent/danger arka plan üstü metin |
| `danger_color`, `danger_bg`, `danger_hover` | Silme/hata durumları |
| `status_planned`, `status_in_progress`, `status_completed` | Kaynak durum rozetleri |
| `tag_badge_bg`, `thumbnail_bg` | Kart içi yardımcı yüzeyler |
| `category_fallback`, `swatch_border` | Kullanıcı kaynaklı renk fallback/sınır değerleri |
| `accent_secondary`, `accent_gradient_start`, `accent_gradient_end` | Canlı primary aksiyon gradientleri |
| `surface_hover`, `surface_elevated`, `focus_ring` | Hover, kart/panel yüzeyi ve focus state |
| `shadow_color`, `muted_badge_bg` | Kart shadow ve düşük vurgu rozet yüzeyleri |
| `success_color`, `warning_color`, `button_pressed`, `nav_selected_bg` | Semantik durumlar ve etkileşim state'leri |

## Dinamik Renk Kurali
- Uygulama kodunda `setStyleSheet()` kullanılmaz; statik görünüm QSS tokenlarıyla yönetilir.
- Kullanıcı/veri kaynaklı renkler QSS string'i olarak yazılmaz. Kart accent şeridi, durum/tag/kategori rozetleri ve kategori renk önizleme kutusu painter tabanlı küçük bileşenlerle çizilir.
- İlgili yardımcılar: `AccentFrame`, `ColorBadge`, `ColorSwatch`, `resolve_theme_color`.

## UI/UX Yenileme Kuralları
- Primary aksiyonlar ve seçili navigasyon state'leri ölçülü gradient kullanır.
- Kart hoverları QSS transition ile değil `AccentFrame.hoverProgress` animasyonu ve shadow/lift etkisiyle verilir.
- Font fallback zinciri: `"Inter", "Segoe UI Variable", "Segoe UI", "Arial"`; mono fallback: `"JetBrains Mono", "Cascadia Code", "Consolas"`.
- Sidebar navigasyon item'ları ikonludur; ikon rengi aktif tema ve seçim durumundan gelir.

## ThemeManager (Singleton) — `core/theme_manager.py`
1. Aktif temayı hafızada tutar.
2. `apply_theme(theme_name)`: QSS'i okur → şablonu doldurur → `QApplication.setStyleSheet()`.
3. `toggle_theme()`: Dark ↔ Light geçiş. Son seçim `QSettings`/`config.json`'a kaydedilir.
4. Tema değişince [[event_bus]] üzerinden `event_bus.theme_changed.emit(theme_dict)` fırlatır.

## İkon Güncelleme (qtawesome)
Bileşen `__init__` içinde `event_bus.theme_changed.connect(self.on_theme_changed)` ile abone olur:

```python
def on_theme_changed(self, theme_data: dict):
    new_icon = qtawesome.icon('fa5s.book', color=theme_data["icon_color"])
    self.my_button.setIcon(new_icon)
```

## Dinamik SVG İkon Boyama
Özel SVG ikonları, dosya içeriğindeki `currentColor` ifadesi aktif tema rengiyle (örn: `Colors.ICON` veya `Colors.ACCENT`) değiştirilerek çalışma zamanında dinamik olarak renklendirilebilir. Bu işlem için `ui/theme_utils.py` içindeki `load_theme_svg(svg_name, color_hex, size)` yardımcı fonksiyonu kullanılır. Bu fonksiyon:
1. `assets/icons/` dizinindeki SVG dosyasını okur.
2. `currentColor` yer tutucularını hedef renk hex kodu ile değiştirir.
3. SVG içeriğini `QSvgRenderer` ile bir `QPixmap` üzerine çizer ve `QIcon` olarak döner.

## QComboBox Ok İkonu (2026-07-06)
`QComboBox`'a herhangi bir QSS (border/background/padding) uygulanınca Qt native ok ikonunu tamamen kaybediyor (bilinen Qt davranışı) — `base.qss`'teki `QComboBox { ... }` kuralı yüzünden tüm combo'larda (StatusCombo, FormCombo, FilterCombo) ok görünmüyordu. `QSS::down-arrow { image: url(...) }` bir **QIcon değil dosya yolu** istediği için `load_theme_svg`'nin QIcon-döndüren mantığı burada kullanılamıyor. Çözüm: `theme_manager.py::apply_theme()`, her tema uygulamasında `assets/icons/chevron_down.svg`'yi (currentColor içerir) o temanın `icon_color`'iyla boyayıp `%APPDATA%/PKM/cache/combo_arrow.svg`'ye yazan bir private `_write_themed_svg()` çalıştırır; sonra `_build_qss()`'e ekstra `combo_arrow_path` anahtarını geçirir, `base.qss`'teki `QComboBox::down-arrow { image: url("{{combo_arrow_path}}"); }` bu dosyayı referans verir. Bu yardımcı bilerek `ui/theme_utils.py`'a değil `core/theme_manager.py`'a eklendi — core katmanının ui'a bağımlı olmaması için (`load_theme_svg` ile ayni boyama mantığını tekrarlar, DRY ihlali kabul edilebilir çünkü katman sınırını korumak öncelikli).

## Özel Tema Geçiş Düğmesi (ToggleSwitch)
Geleneksel buton yerine `ui/components/toggle_switch.py` altında tanımlanmış animasyonlu `ToggleSwitch` bileşeni kullanılır. Bu bileşen:
- `QPropertyAnimation` ile butonun kayma hareketini akıcı şekilde canlandırır.
- `paintEvent` içinde aktif temanın renklerine göre (`accent_color`, `border_color`, `bg_primary`) çizim yapar.
- Tema değiştiğinde durumunu otomatik senkronize eder.

## UX
- Sidebar alt kısmında özel `ToggleSwitch` ile tema değişimi sağlanır.
- İlk açılışta kayıtlı tema yüklenir (uygulama başlangıcında `ThemeManager.apply_theme(saved_theme)`).

## İlgili Sayfalar
[[event_bus]] · [[mimari_kurallari]] · [[ui_layout]] · [[dizin_yapisi]]

