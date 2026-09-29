# -*- coding: utf-8 -*-
class AppStrings:
    APP_TITLE = "Kişisel Bilgi Yöneticisi"

    # Sidebar
    INBOX = "Gelen Kutusu"
    PLANNED = "Planlananlar"
    URL_SHOWCASE = "Bağlantı Vitrini"
    FAVORITES = "Favoriler"
    TOGGLE_THEME = "Tema Değiştir"
    TOGGLE_SIMPLE_MODE = "Sade Mod"

    # Toolbar
    SEARCH_PLACEHOLDER = "Ara..."
    ADD_NEW = "Yeni Ekle"

    # Ayarlar sayfası
    SETTINGS = "Ayarlar"
    SETTINGS_CATEGORIES_TAB = "Kategoriler"
    SETTINGS_TAGS_TAB = "Etiketler"
    CATEGORY_NAME = "Kategori adı"
    CATEGORY_COLOR = "Renk (#RRGGBB)"
    CATEGORY_ICON = "İkon (opsiyonel)"
    TAG_NAME = "Etiket adı"
    ADD = "Ekle"
    EDIT = "Düzenle"
    DELETE = "Sil"
    CONFIRM_DELETE = "Silmek için tekrar tıkla"
    EMPTY_CATEGORIES_MSG = "Henüz kategori eklenmedi. Aşağıdan yeni bir kategori oluşturabilirsiniz."
    EMPTY_TAGS_MSG = "Henüz etiket eklenmedi. Aşağıdan yeni bir etiket oluşturabilirsiniz."

    # Detail panel
    OPEN_IN_BROWSER = "Tarayıcıda Aç"
    CLOSE_PANEL = "Kapat"
    STATUS_LABEL = "Durum"

    # Status values
    STATUS_PLANNED = "Planlandı"
    STATUS_IN_PROGRESS = "Devam Ediyor"
    STATUS_COMPLETED = "Tamamlandı"

    # Empty state
    EMPTY_STATE_MSG = "Burada henüz bir şey yok. Yeni Ekle'ye basarak ilk kaynağınızı oluşturun."

    # Form — Yeni Kaynak
    FORM_HEADER = "Yeni Kaynak Ekle"
    FORM_FIELD_TITLE = "Başlık *"
    FORM_FIELD_URL = "URL (opsiyonel)"
    FORM_FIELD_CATEGORY = "Kategori"
    FORM_FIELD_PRIORITY = "Öncelik"
    FORM_FIELD_TAGS = "Etiketler (virgülle ayır)"
    FORM_FIELD_CONTENT = "Not / Açıklama"
    FORM_PRIORITY_LOW = "3 — Düşük"
    FORM_PRIORITY_MEDIUM = "2 — Orta"
    FORM_PRIORITY_HIGH = "1 — Yüksek"
    FORM_CATEGORY_NONE = "— Seçiniz —"
    FORM_ADD_CATEGORY_TOOLTIP = "Yeni kategori ekle"
    SAVE = "Kaydet"
    CANCEL = "İptal"

    # Form — Düzenle
    FORM_HEADER_EDIT = "Kaynağı Düzenle"
    FORM_FIELD_STATUS = "Durum"
    FORM_STATUS_INBOX = "Gelen Kutusu"
    FORM_STATUS_PLANNED = "Planlandı"
    FORM_STATUS_IN_PROGRESS = "Devam Ediyor"
    FORM_STATUS_COMPLETED = "Tamamlandı"
    EDIT_RESOURCE = "Düzenle"
    DELETE_RESOURCE = "Sil"
    CONFIRM_DELETE_RESOURCE = "Silmek için tekrar tıkla"
    SAVE_NOTES = "Notu Kaydet"

    # Errors
    ERR_TITLE_REQUIRED = "Başlık boş bırakılamaz."
    ERR_COLOR_REQUIRED = "Renk seçilmelidir."
    ERR_CATEGORY_NAME_REQUIRED = "Kategori adı zorunludur."

    # Renk seçici
    PICK_COLOR_PLACEHOLDER = "Renk seç..."
    PICK_COLOR_TITLE = "Kategori rengini seçin"

    # Filtre çubuğu
    FILTER_CATEGORY = "Kategori"
    FILTER_TAG = "Etiket"
    FILTER_STATUS = "Durum"
    FILTER_PRIORITY = "Öncelik"
    FILTER_ANY = "Hepsi"
    FILTER_CLEAR = "Temizle"
    FILTER_TAG_PLACEHOLDER = "Etiket seç..."

    # Pin / Favori
    PIN_TOOLTIP = "Sabitle"
    UNPIN_TOOLTIP = "Sabitlemeyi kaldır"
    FAVORITE_TOOLTIP = "Favoriye ekle"
    UNFAVORITE_TOOLTIP = "Favoriden çıkar"

    # Okuyucu
    READ_RESOURCE = "Oku"
    READER_HIGHLIGHT_ACTION = "Alıntı olarak kaydet"
    READER_VOCAB_ACTION = "Kelime olarak kaydet"
    READER_BACK = "Geri"
    READER_EMPTY_MSG = "Bu kaynak için henüz metin yok."
    READER_VOCAB_TRANSLATION_PLACEHOLDER = "Türkçe çeviri"
    READER_READING_TIME_FMT = "{minutes} dk okuma"
    READER_FONT_DECREASE_TOOLTIP = "Yazıyı küçült"
    READER_FONT_INCREASE_TOOLTIP = "Yazıyı büyüt"
    READER_DELETE_HIGHLIGHT_TOOLTIP = "Alıntıyı sil"

    # Makale Market
    ARTICLE_MARKET = "Makale Market"
    MARKET_SEARCH_PLACEHOLDER = "Bir konu ara (örn. transformer neural network)..."
    MARKET_SEARCH_BUTTON = "Ara"
    MARKET_TAB_RECENT = "En Güncel"
    MARKET_TAB_POPULAR = "En Popüler"
    MARKET_TAB_CITED = "En Çok Atıf Alan"
    MARKET_EMPTY_MSG = "Bir konu arayarak makale keşfetmeye başlayın."
    MARKET_NO_RESULTS_MSG = "Sonuç bulunamadı."
    MARKET_SEARCHING_MSG = "Aranıyor..."
    MARKET_CITATION_FMT = "{count} atıf"
    MARKET_SAVED_LABEL = "Kaydedildi"
    MARKET_LOAD_MORE = "Daha fazla yükle"
    MARKET_RETRY = "Tekrar dene"
    MARKET_SEARCH_FAILED = "Sonuçlar alınamadı. Bağlantını kontrol edip tekrar dene."
    MARKET_RECENT_SEARCHES = "Son aramalar"
    MARKET_CLEAR_HISTORY = "Temizle"
    NOTIFICATION_MARKET_SAVED_FMT = "'{title}' kaydedildi."
    NOTIFICATION_MARKET_DUPLICATE_FMT = "'{title}' zaten kütüphanende."
    NOTIFICATION_MARKET_BATCH_SAVED_FMT = "{saved} makale kaydedildi."
    NOTIFICATION_MARKET_BATCH_SKIPPED_FMT = "{saved} makale kaydedildi, {skipped} tanesi zaten kütüphanendeydi."
    NOTIFICATION_MARKET_BATCH_ALL_DUPLICATE = "Seçilen makalelerin hepsi zaten kütüphanende."
    NOTIFICATION_MARKET_EXPORT_EMPTY = "Dışa aktarılacak sonuç yok."
    NOTIFICATION_SAVED_SEARCH_SAVED_FMT = "Arama kaydedildi: {label}"
    MARKET_READ_LATER_TAG = "okuma-listesi"

    # Yerel PDF ice aktarma
    DROP_PDF_HINT = "PDF'i buraya bırak"
    NOTIFICATION_PDF_IMPORT_INVALID = "Sadece PDF dosyaları desteklenir."
    NOTIFICATION_PDF_IMPORT_FAILED = "PDF kopyalanamadı."
    NOTIFICATION_PDF_IMPORTED_FMT = "'{title}' içeri aktarıldı."

    # Bilgi Havuzu
    KNOWLEDGE_POOL = "Bilgi Havuzu"
    KNOWLEDGE_POOL_HIGHLIGHTS_TAB = "Alıntılar"
    KNOWLEDGE_POOL_VOCAB_TAB = "Kelime Dağarcığı"
    EMPTY_HIGHLIGHTS_MSG = "Henüz alıntı kaydedilmedi."
    EMPTY_VOCAB_MSG = "Henüz kelime kaydedilmedi."

    # Bildirimler
    NOTIFICATION_NOTES_SAVED = "Notlar kaydedildi."
    NOTIFICATION_RESOURCE_DELETED = "Kaynak silindi."
    NOTIFICATION_HIGHLIGHT_SAVED = "Alıntı kaydedildi."
    NOTIFICATION_HIGHLIGHT_DELETED = "Alıntı silindi."
    NOTIFICATION_HIGHLIGHTS_DELETED_FMT = "{count} alıntı silindi."
    NOTIFICATION_VOCAB_SAVED_FMT = "'{word}' kelime havuzuna eklendi."
    NOTIFICATION_VOCAB_DELETED = "Kelime silindi."
    NOTIFICATION_RESOURCE_SAVED_FMT = "Kaynak başarıyla {action}."
    NOTIFICATION_ACTION_SAVED = "kaydedildi"
    NOTIFICATION_ACTION_UPDATED = "güncellendi"
    NOTIFICATION_CATEGORY_ADDED_FMT = "'{name}' kategorisi eklendi."
    NOTIFICATION_CATEGORY_UPDATED = "Kategori güncellendi."
    NOTIFICATION_CATEGORY_DELETED = "Kategori silindi."
    NOTIFICATION_TAG_ADDED_FMT = "#{name} etiketi eklendi."
    NOTIFICATION_TAG_UPDATED = "Etiket güncellendi."
    NOTIFICATION_TAG_DELETED = "Etiket silindi."
    NOTIFICATION_INVALID_FORM_DATA = "Kategori veya öncelik değeri geçersiz."
    NOTIFICATION_PDF_DOWNLOAD_FAILED = "PDF indirilemedi, metin okuyucusunda açılıyor."
    NOTIFICATION_CITATION_COPIED_FMT = "Atıf panoya kopyalandı ({style})."
    NOTIFICATION_PAPER_LOOKUP_FAILED = "Makale bilgisi getirilemedi (ağ/servis hatası)."
    NOTIFICATION_PAPER_NOT_FOUND = "OpenAlex'te eşleşen makale bulunamadı."
    NOTIFICATION_PAPER_METADATA_SAVED = "Makale bilgileri güncellendi."
    NOTIFICATION_EXPORT_DONE_FMT = "Dışa aktarıldı: {name}"
    NOTIFICATION_EXPORT_FAILED = "Dışa aktarım yazılamadı."
    NOTIFICATION_EXPORT_EMPTY = "Dışa aktarılacak alıntı, not veya kelime bulunamadı."
    RELATED_PAPERS_LOAD_FAILED = "Liste yüklenemedi. Bağlantını kontrol edip tekrar dene."
    ERR_CATEGORY_NAME_EMPTY = "Kategori adı boş olamaz."
    ERR_TAG_NAME_EMPTY = "Etiket adı boş olamaz."
