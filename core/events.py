from PySide6.QtCore import QObject, Signal


class _EventBus(QObject):
    """Merkezi olay yonetici — Singleton + Observer deseni.

    UI bilesenleri birbirini dogrudan referans almaz;
    tüm durum degisiklikleri bu sinif üzerinden akar.
    """

    # --- Kaynak (Resource) sinyalleri ---
    resource_added = Signal(int)      # yeni kaynak ID'si
    resource_updated = Signal(int)    # güncellenen kaynak ID'si
    resource_deleted = Signal(int)    # silinen kaynak ID'si

    # --- Kategori sinyalleri ---
    category_added = Signal(int)
    category_updated = Signal(int)
    category_deleted = Signal(int)

    # --- Etiket sinyalleri ---
    tag_added = Signal(int)
    tag_updated = Signal(int)
    tag_deleted = Signal(int)

    # --- Alinti (Highlight) sinyalleri ---
    highlight_added = Signal(int)
    highlight_updated = Signal(int)
    highlight_deleted = Signal(int)

    # --- Kelime (Vocabulary) sinyalleri ---
    vocabulary_added = Signal(int)
    vocabulary_deleted = Signal(int)

    # --- PDF Notu sinyalleri ---
    pdf_note_added = Signal(int)
    pdf_note_updated = Signal(int)
    pdf_note_deleted = Signal(int)

    # --- Kayitli arama (Makale Market) sinyali ---
    saved_search_changed = Signal()

    # --- Hata sinyali ---
    error_occurred = Signal(str)          # kullanici arayüzüne iletilecek hata mesaji


event_bus = _EventBus()
