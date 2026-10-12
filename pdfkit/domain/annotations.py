from dataclasses import dataclass, field
from datetime import datetime

# Capa durumlari
STATUS_OK = "ok"  # konum dogrulandi
STATUS_PENDING = "pending_context"  # eski kayit: konum var, onceki/sonraki baglam henuz cikarilmadi
STATUS_ORPHANED = "orphaned"  # metin bulunamadi; kullanici yeniden baglayabilir
STATUS_UNANCHORED = "unanchored"  # konumu hic yok (eski kelimeler)

Polygon = list[tuple[float, float]]


@dataclass(frozen=True)
class Segment:
    """Alintinin tek sayfadaki parcasi: Qt PDFium metin indeksi araligi [start, end) + o parcanin metni.

    `polygons` sayfa noktasi (pt) uzayinda onbellege alinmis geometridir (yakinlastirmadan bagimsiz);
    `Annotation.engine_fp` ile uretildigi motor surumune baglidir."""

    page: int
    start: int
    end: int
    text: str = ""
    polygons: list[Polygon] | None = None


@dataclass
class Annotation:
    """Metin alintisi (vurgu). Her alinti kararli bir `uid` tasir."""

    id: int
    uid: str
    document_id: int
    label_key: str
    color: str | None
    comment: str | None
    tags: list[str]
    quote_exact: str
    quote_prefix: str | None
    quote_suffix: str | None
    segments: list[Segment]
    engine_fp: str | None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    legacy_id: int | None = None

    @property
    def page(self) -> int | None:
        return self.segments[0].page if self.segments else None


@dataclass
class PageNote:
    """Sayfada bir noktaya yapisan serbest not (sayfa noktasi uzayinda x, y)."""

    id: int
    uid: str
    document_id: int
    page: int
    x: float
    y: float
    text: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    legacy_id: int | None = None


@dataclass
class Term:
    """Yabanci dildeki PDF'ten kaydedilen bilinmeyen kelime/ifade; gectigi cumleyle birlikte."""

    id: int
    uid: str
    document_id: int
    word: str
    translation: str
    context_sentence: str | None
    mastery_level: int
    segments: list[Segment] = field(default_factory=list)
    status: str = STATUS_UNANCHORED
    engine_fp: str | None = None
    created_at: datetime | None = None
    legacy_id: int | None = None
