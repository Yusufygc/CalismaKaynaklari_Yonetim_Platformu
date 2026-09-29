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

    # --- UI etkilesim sinyalleri ---
    resource_selected = Signal(int)       # karta tiklandı → sag panel ac
    search_query_changed = Signal(str)    # arama cubugu metni degisti
    sidebar_filter_changed = Signal(str)  # sol menü secimi degisti (kategori adi veya sabit filtre)
    resource_pin_toggle_requested = Signal(int)      # karttaki pin ikonu tiklandı
    resource_favorite_toggle_requested = Signal(int) # karttaki yildiz ikonu tiklandı
    filters_changed = Signal(dict)        # FilterBar → ContentWorkspace

    # --- Tema sinyali ---
    theme_changed = Signal(dict)          # aktif tema renk sözlügü
    simple_mode_toggled = Signal(bool)    # sidebar'daki "Sade Mod" toggle'i degisti

    # --- Hata sinyali ---
    error_occurred = Signal(str)          # kullanici arayüzüne iletilecek hata mesaji


event_bus = _EventBus()
