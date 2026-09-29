# Event Bus (Sinyal ve Olay Yönetimi)

## Mimari
- **Desen:** Singleton + Observer (`QObject` üzerinden)
- **Dosya:** `core/events.py`
- UI bileşenleri birbirini **doğrudan referans almaz** — her durum değişikliği merkezi bus üzerinden iletilir.

---

## Tanımlı Sinyaller

### Kaynak Sinyalleri
| Sinyal | Tip | Tetiklenme |
|--------|-----|-----------|
| `resource_added` | `Signal(int)` | Yeni kaynak eklendi — id taşır |
| `resource_updated` | `Signal(int)` | Kaynak güncellendi — id taşır |
| `resource_deleted` | `Signal(int)` | Kaynak silindi — id taşır |

### Kategori Sinyalleri
| Sinyal | Tip | Tetiklenme |
|--------|-----|-----------|
| `category_added` | `Signal(int)` | Yeni kategori — id taşır |
| `category_updated` | `Signal(int)` | Kategori güncellendi |
| `category_deleted` | `Signal(int)` | Kategori silindi |

### Etiket Sinyalleri
| Sinyal | Tip | Tetiklenme |
|--------|-----|-----------|
| `tag_added` | `Signal(int)` | Yeni etiket — id taşır |
| `tag_updated` | `Signal(int)` | Etiket güncellendi |
| `tag_deleted` | `Signal(int)` | Etiket silindi |

### Alıntı (Highlight) / Kelime (Vocabulary) Sinyalleri — 2026-07-06
| Sinyal | Tip | Tetiklenme |
|--------|-----|-----------|
| `highlight_added` | `Signal(int)` | Okuyucuda metin seçilip "Alıntı olarak kaydet" ile oluşturuldu |
| `highlight_deleted` | `Signal(int)` | Bilgi Havuzu'nda 2-tıkla silindi |
| `vocabulary_added` | `Signal(int)` | Okuyucuda kelime seçilip çeviri girilerek oluşturuldu |
| `vocabulary_deleted` | `Signal(int)` | Bilgi Havuzu'nda 2-tıkla silindi |

Not: düzenleme sinyali yok (`_updated`) — bu iki varlık bu turda sadece oluşturulup silinebiliyor. `KnowledgePoolView` bu 4 sinyale abone olup listesini otomatik tazeler.

### Hata Sinyali
| Sinyal | Tip | Tetiklenme |
|--------|-----|-----------|
| `error_occurred` | `Signal(str)` | Herhangi bir işlem hatası — ContentView / SettingsView banner gösterir |

---

## Kullanım Kuralları
- **Emit:** Controller, servis işlemi başarılı olduktan **hemen sonra** sinyal fırlatır.
- **Connect:** View / bileşen `__init__` içinde bus'a abone olur. Bridge'lerde yalnızca QObject'e bağlı metotlarla (lambda değil) bağlanılır; alt-bridge dinleyicileri: `LibraryBridge` (`resource_*`, `category_updated/deleted`, `tag_updated/deleted`), `ReaderBridge` (`highlight_*`, `vocabulary_*`, `resource_deleted`, `category_*`, `tag_*`), `MarketBridge` (`saved_search_changed`), `LibraryIndexCache` (`resource_*`), kök `QmlBridge` (`error_occurred` → toast).
- **Bellek:** Bileşen yok edilirken `disconnect()` çağrılmalı veya PySide6 parent-child yaşam döngüsüne güvenilmeli.
- **error_occurred:** Controller `try/except` bloklarında hata → `event_bus.error_occurred.emit(str(exc))`. Banner bileşeni (InlineBanner) bunu yakalar.

---

## Örnek Kullanım

```python
# Emit (Controller tarafında)
event_bus.resource_updated.emit(resource.id)

# Connect (View tarafında)
event_bus.resource_updated.connect(self._reload)

# Hata yayını
event_bus.error_occurred.emit("Kaynak bulunamadı.")
```

## İlgili Sayfalar
[[qml_arayuz]] · [[core_servisler]] · [[mimari_kurallari]]

> 2026-09-30: UI'ya dair kullanılmayan 8 sinyal (`resource_selected`, `sidebar_filter_changed`, `search_query_changed`, `resource_pin_toggle_requested`, `resource_favorite_toggle_requested`, `filters_changed`, `theme_changed`, `simple_mode_toggled`) ölü kod olarak kaldırıldı; bu işler artık QML → `bridge` slotlarıyla yürütülür.
