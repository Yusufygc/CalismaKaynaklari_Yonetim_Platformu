# -*- coding: utf-8 -*-
class AppStrings:
    # Durum adları
    FORM_STATUS_INBOX = "Gelen Kutusu"
    FORM_STATUS_PLANNED = "Planlandı"
    FORM_STATUS_IN_PROGRESS = "Devam Ediyor"
    FORM_STATUS_COMPLETED = "Tamamlandı"

    # Makale Market
    NOTIFICATION_MARKET_SAVED_FMT = "'{title}' kaydedildi."
    NOTIFICATION_MARKET_DUPLICATE_FMT = "'{title}' zaten kütüphanende."
    NOTIFICATION_MARKET_BATCH_SAVED_FMT = "{saved} makale kaydedildi."
    NOTIFICATION_MARKET_BATCH_SKIPPED_FMT = "{saved} makale kaydedildi, {skipped} tanesi zaten kütüphanendeydi."
    NOTIFICATION_MARKET_BATCH_ALL_DUPLICATE = "Seçilen makalelerin hepsi zaten kütüphanende."
    NOTIFICATION_MARKET_EXPORT_EMPTY = "Dışa aktarılacak sonuç yok."
    NOTIFICATION_SAVED_SEARCH_SAVED_FMT = "Arama kaydedildi: {label}"
    MARKET_READ_LATER_TAG = "okuma-listesi"

    # Yerel PDF ice aktarma
    NOTIFICATION_PDF_IMPORT_INVALID = "Sadece PDF dosyaları desteklenir."
    NOTIFICATION_PDF_IMPORT_FAILED = "PDF kopyalanamadı."
    NOTIFICATION_PDF_DUPLICATE_FMT = "'{title}' zaten kütüphanede."
    NOTIFICATION_PDF_NO_TEXT_LAYER = (
        "Bu PDF'in metin katmanı yok (taranmış olabilir): metin seçimi, arama ve alıntı çalışmaz."
    )
    NOTIFICATION_PDF_IMPORTED_FMT = "'{title}' içeri aktarıldı."

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
    NOTIFICATION_URL_DUPLICATE_FMT = "Bu bağlantı zaten kayıtlı: '{title}'."
    NOTIFICATION_INVALID_FORM_DATA = "Kategori veya öncelik değeri geçersiz."
    NOTIFICATION_PDF_DOWNLOAD_FAILED = "PDF indirilemedi, metin okuyucusunda açılıyor."
    NOTIFICATION_CITATION_COPIED_FMT = "Atıf panoya kopyalandı ({style})."
    NOTIFICATION_PAPER_LOOKUP_FAILED = "Makale bilgisi getirilemedi (ağ/servis hatası)."
    NOTIFICATION_PAPER_NOT_FOUND = "OpenAlex'te eşleşen makale bulunamadı."
    NOTIFICATION_PAPER_METADATA_SAVED = "Makale bilgileri güncellendi."
    NOTIFICATION_EXPORT_DONE_FMT = "Dışa aktarıldı: {name}"
    NOTIFICATION_EXPORT_FAILED = "Dışa aktarım yazılamadı."
    NOTIFICATION_LINK_BLOCKED = "Bu bağlantı güvenlik nedeniyle açılmadı (yalnızca web ve e-posta bağlantıları açılır)."
    NOTIFICATION_EXPORT_EMPTY = "Dışa aktarılacak alıntı, not veya kelime bulunamadı."
    RELATED_PAPERS_LOAD_FAILED = "Liste yüklenemedi. Bağlantını kontrol edip tekrar dene."
