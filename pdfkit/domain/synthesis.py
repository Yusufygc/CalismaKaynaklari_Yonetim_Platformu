"""Literatur matrisi: satir = makale, sutun = anlam etiketi, hucre = o makalenin o turdeki alintilari. Saf Python.

Matris, "tum makalelerin yontemlerini yan yana karsilastir" gibi sentez sorularinin cevabidir. Bu modul veriyi (satirlar) ve
suzgecleri (etiket alt kumesi, serbest etiket, kaynak alt kumesi) bilir; veritabani, dosya ya da Qt bilmez. Cikti
Markdown tablosudur (Obsidian'da okunur); icerigi dis girdi sayar ve tabloyu bozabilecek her seyi kacirir."""
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace

from pdfkit.domain.annotations import STATUS_ORPHANED, Annotation
from pdfkit.domain.citekey import base_citekey, make_unique
from pdfkit.domain.labels import GENERAL_KEY, GENERAL_NAME, LABELS, is_known_label, name_for_label
from pdfkit.domain.models import Document, SourceInfo
from pdfkit.domain.search import fold
from pdfkit.domain.vault_note import annotation_sort_key, inline_text, page_link

MAX_QUOTE_LENGTH = 220
CELL_SEPARATOR = "<br>"


def column_keys() -> tuple[str, ...]:
    """Matris sutunlari: bes anlam etiketi (tanim sirasiyla) + genel."""
    return tuple(label.key for label in LABELS) + (GENERAL_KEY,)


def ordered_columns(order: Sequence[str] | None = None) -> tuple[str, ...]:
    """`order`daki bilinen sutunlar (tekrarsiz) verilen sirayla, eksik kalanlar varsayilan sirayla sona eklenir. Bilinmeyen
    anahtarlar atilir; boylece bozuk bir ayar matrisi bozmaz."""
    known = column_keys()
    chosen = list(dict.fromkeys(key for key in (order or ()) if key in known))
    return tuple(chosen) + tuple(key for key in known if key not in chosen)


DEFAULT_VAULT_CELL_LIMIT = 10


@dataclass(frozen=True)
class MatrixOptions:
    """Kullanici ayarlari: `order` sutun sirasi (bos = varsayilan); `vault_columns` Obsidian `_Matris.md`'ye yazilacak
    sutunlar (None = hepsi); `cell_limit` o dosyada hucre basina en cok alinti (0 = hepsi). Uygulama ici matris ve
    disa aktarma yalniz `order`i kullanir (hucre siniri yok)."""

    order: tuple[str, ...] = field(default_factory=tuple)
    vault_columns: tuple[str, ...] | None = None
    cell_limit: int = DEFAULT_VAULT_CELL_LIMIT

    @classmethod
    def normalized(cls, order=None, vault_columns=None, cell_limit=DEFAULT_VAULT_CELL_LIMIT) -> "MatrixOptions":
        """Disaridan (ayar dosyasi) gelen degerleri guvenli hale getirir: bilinmeyen anahtarlar atilir, sinir 0..200."""
        known = column_keys()
        ordered = ordered_columns(order if isinstance(order, (list, tuple)) else ())
        chosen = (
            tuple(key for key in ordered if key in vault_columns) if isinstance(vault_columns, (list, tuple)) else None
        )
        limit = cell_limit if isinstance(cell_limit, int) and not isinstance(cell_limit, bool) else DEFAULT_VAULT_CELL_LIMIT
        return cls(ordered if tuple(ordered) != known else (), chosen, max(0, min(limit, 200)))


@dataclass(frozen=True)
class MatrixRow:
    """Bir belgenin tum alintilari etiketlerine gore gruplu (suzgec uygulanmamis)."""

    document: Document
    title: str
    year: int | None
    citekey: str | None
    resource_id: int | None
    cells: Mapping[str, tuple[Annotation, ...]]
    authors: tuple[str, ...] = ()
    provisional_citekey: str | None = None  # vault notu henuz yokken ONERILEN anahtar (hicbir yere yazilmaz, baglanti uretmez)

    @property
    def annotation_count(self) -> int:
        return sum(len(items) for items in self.cells.values())


@dataclass(frozen=True)
class MatrixFilter:
    """`labels`: gosterilecek sutunlar (None = hepsi); `tag`: yalniz bu serbest etiketi tasiyan alintilar; `document_ids`:
    yalniz bu belgeler (None = hepsi)."""

    labels: tuple[str, ...] | None = None
    tag: str | None = None
    document_ids: frozenset[int] | None = None


@dataclass(frozen=True)
class Matrix:
    columns: tuple[str, ...]
    rows: tuple[MatrixRow, ...]

    @property
    def annotation_count(self) -> int:
        return sum(row.annotation_count for row in self.rows)


def build_row(
    document: Document,
    info: SourceInfo,
    citekey: str | None,
    annotations: Iterable[Annotation],
    resource_id: int | None = None,
) -> MatrixRow:
    """Bir belgenin alintilarini etiketlerine gore gruplar. Bilinmeyen etiket 'genel' sutununa duser."""
    grouped: dict[str, list[Annotation]] = {key: [] for key in column_keys()}
    for annotation in annotations:
        key = annotation.label_key if is_known_label(annotation.label_key) else GENERAL_KEY
        grouped[key].append(annotation)
    cells = {key: tuple(sorted(items, key=annotation_sort_key)) for key, items in grouped.items() if items}
    title = info.title or document.pdf_title or document.original_filename or ""
    return MatrixRow(document, title, info.year, citekey, resource_id, cells, tuple(info.authors))


def with_provisional_citekeys(rows: Iterable[MatrixRow]) -> list[MatrixRow]:
    """Atıf anahtarı (citekey) henuz atanmamis satirlara onerilen anahtar ekler: vault notu olusunca alinacak anahtarin
    tahmini (ayni uretici). Belge kimligi sirasiyla ve gercek/oneri anahtarlariyla cakismadan uretilir, yani ayni veriden
    hep ayni sonuc cikar. Veritabanina yazilmaz; gercek atama vault esitlemesindedir."""
    items = list(rows)
    taken = {row.citekey for row in items if row.citekey}
    suggestions: dict[int, str] = {}
    for row in sorted((r for r in items if not r.citekey), key=lambda r: r.document.id):
        document = row.document
        key = make_unique(base_citekey(row.authors, row.year, row.title or document.pdf_title or "", document.pdf_author), taken)
        taken.add(key)
        suggestions[document.id] = key
    return [replace(row, provisional_citekey=suggestions.get(row.document.id)) if not row.citekey else row for row in items]


def _normalize_tag(tag: str | None) -> str:
    return (tag or "").strip().lstrip("#").strip().lower()


def make_matrix(rows: Iterable[MatrixRow], matrix_filter: MatrixFilter | None = None, order: Sequence[str] | None = None) -> Matrix:
    """Suzgeci uygular: sutunlari kisitlar, alintilari etikete gore eler, hicbir alintisi kalmayan satiri atar.
    Satirlar citekey sirasiyla (citekey'i olmayanlar sonda, basliga gore). Sutunlar `order` sirasindadir."""
    flt = matrix_filter or MatrixFilter()
    all_columns = ordered_columns(order)
    columns = tuple(key for key in all_columns if flt.labels is None or key in flt.labels)
    tag = _normalize_tag(flt.tag)
    kept: list[MatrixRow] = []
    for row in rows:
        if flt.document_ids is not None and row.document.id not in flt.document_ids:
            continue
        cells = {}
        for key in columns:
            items = tuple(a for a in row.cells.get(key, ()) if not tag or tag in a.tags)
            if items:
                cells[key] = items
        if cells:
            kept.append(replace(row, cells=cells))
    kept.sort(key=lambda r: (r.citekey is None, r.citekey or "", r.title.casefold(), r.document.id))
    return Matrix(columns, tuple(kept))


def document_ids_matching(rows: Iterable[MatrixRow], query: str | None) -> frozenset[int] | None:
    """Baslik/citekey/yil Turkce-duyarsiz alt metin eslesmesiyle kaynak suzgeci icin belge kimlikleri; sorgu bos ise
    None (suzgec yok)."""
    wanted = fold((query or "").strip())
    if not wanted:
        return None
    return frozenset(
        row.document.id for row in rows if wanted in fold(f"{row.title} {row.citekey or ''} {row.year or ''}")
    )


def tag_counts(rows: Iterable[MatrixRow]) -> list[tuple[str, int]]:
    """Alintilardaki serbest etiketler ve sayilari (cok kullanilandan aza, esitlikte ada gore)."""
    counts: dict[str, int] = {}
    for row in rows:
        for items in row.cells.values():
            for annotation in items:
                for tag in annotation.tags:
                    counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


# ---------------------------------------------------------------------- #
# Markdown
# ---------------------------------------------------------------------- #


def _cell_text(text: str) -> str:
    """Tablo hucresi icin guvenli metin: tek satir, `%%` etkisiz, `|` ve `<` `>` kacirilmis."""
    cleaned = inline_text(text).replace("\\", "\\\\")  # ters bolu once: yoksa `\|` kacisi bozulur
    return cleaned.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def shorten(text: str) -> str:
    return text if len(text) <= MAX_QUOTE_LENGTH else text[: MAX_QUOTE_LENGTH - 1].rstrip() + "…"


def quote_markdown(document: Document, annotation: Annotation) -> str:
    """Hucredeki tek alinti: `• “alinti” ([s. 3](pkm://…)) — yorum`."""
    line = f"• “{shorten(_cell_text(annotation.quote_exact))}”"
    if annotation.status != STATUS_ORPHANED and annotation.page is not None:
        line += f" ({page_link(document, annotation.page, annotation.uid)})"
    comment = _cell_text(annotation.comment or "")
    if comment:
        line += f" — {shorten(comment)}"
    return line


def row_header(row: MatrixRow) -> str:
    title = _cell_text(row.title) or (row.citekey or "İsimsiz")
    year = f" ({row.year})" if row.year else ""
    return f"[[{row.citekey}]] · {title}{year}" if row.citekey else f"{title}{year}"


def column_name(key: str) -> str:
    return GENERAL_NAME if key == GENERAL_KEY else name_for_label(key)


def _cell_markdown(row: MatrixRow, key: str, cell_limit: int) -> str:
    items = row.cells.get(key, ())
    shown = items[:cell_limit] if cell_limit > 0 else items
    parts = [quote_markdown(row.document, a) for a in shown]
    if len(shown) < len(items):
        parts.append(f"… ve {len(items) - len(shown)} alıntı daha (uygulamada)")
    return CELL_SEPARATOR.join(parts)


def render_table(matrix: Matrix, cell_limit: int = 0) -> list[str]:
    """Matrisin Markdown tablosu (satir listesi). Satir yoksa bos liste. `cell_limit` > 0 ise hucre basina en cok o kadar
    alinti yazilir, fazlasi "… ve N alinti daha" satiriyla belirtilir (0 = hepsi)."""
    if not matrix.rows:
        return []
    header = ["Kaynak"] + [column_name(key) for key in matrix.columns]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for row in matrix.rows:
        cells = [_cell_markdown(row, key, cell_limit) for key in matrix.columns]
        lines.append("| " + " | ".join([row_header(row)] + cells) + " |")
    return lines


def matrix_summary(matrix: Matrix) -> str:
    return f"{len(matrix.rows)} kaynak · {matrix.annotation_count} alıntı"


def render_markdown(matrix: Matrix, title: str = "Literatür Matrisi", note: str = "") -> str:
    """Disa aktarilacak tam Markdown (baslik + ozet + varsa suzgec notu + tablo). Satir yoksa yalniz baslik ve aciklama."""
    lines = [f"# {title}", ""]
    table = render_table(matrix)
    if not table:
        return "\n".join(lines + ["_Eşleşen alıntı yok._"]) + "\n"
    summary = [f"_{matrix_summary(matrix)}_"] + ([f"_Süzgeç: {_cell_text(note)}_"] if note else [])
    return "\n".join(lines + summary + [""] + table) + "\n"

