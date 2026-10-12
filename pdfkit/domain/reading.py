from dataclasses import dataclass

MIN_ZOOM = 0.1
MAX_ZOOM = 10.0
ACTIVE_GAP_SECONDS = 60  # iki kayit arasi bu kadardan uzunsa kullanici aktif sayilmaz


@dataclass(frozen=True)
class ReadingState:
    """Bir belgede kalinan yer: sayfa + sayfa ici konum (sayfa noktasi uzayi) + yakinlastirma; ayrica en uzak
    sayfa (ilerleme) ve aktif okuma suresi."""

    document_id: int
    last_page: int
    loc_x: float
    loc_y: float
    zoom: float
    max_page: int
    total_seconds: int

    def progress(self, page_count: int) -> float:
        return progress_ratio(self.max_page, page_count)


def progress_ratio(max_page: int, page_count: int) -> float:
    """Okunan oran: (en uzak sayfa + 1) / sayfa sayisi; 0..1."""
    if page_count <= 0:
        return 0.0
    return min(1.0, max(0.0, (max_page + 1) / page_count))
