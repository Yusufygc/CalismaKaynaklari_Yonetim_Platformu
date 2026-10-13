"""Literatur matrisi: satir = makale, sutun = anlam etiketi, hucre = o makalenin o turdeki alintilari. Saf Python.

Matris, "tum makalelerin yontemlerini yan yana karsilastir" gibi sentez sorularinin cevabidir. Bu modul veriyi (satirlar) ve
suzgecleri (etiket alt kumesi, serbest etiket, kaynak alt kumesi) bilir; veritabani, dosya ya da Qt bilmez. Cikti
Markdown tablosudur (Obsidian'da okunur); icerigi dis girdi sayar ve tabloyu bozabilecek her seyi kacirir."""
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from pdfkit.domain.annotations import STATUS_ORPHANED, Annotation
from pdfkit.domain.labels import GENERAL_KEY, GENERAL_NAME, LABELS, is_known_label, name_for_label
from pdfkit.domain.models import Document, SourceInfo
from pdfkit.domain.vault_note import annotation_sort_key, inline_text, page_link

MAX_QUOTE_LENGTH = 220
CELL_SEPARATOR = "<br>"


def column_keys() -> tuple[str, ...]:
    """Matris sutunlari: bes anlam etiketi (tanim sirasiyla) + genel."""
    return tuple(label.key for label in LABELS) + (GENERAL_KEY,)


@dataclass(frozen=True)
class MatrixRow:
    """Bir belgenin tum alintilari etiketlerine gore gruplu (suzgec uygulanmamis)."""

    document: Document
    title: str
    year: int | None
    citekey: str | None
    resource_id: int | None
    cells: Mapping[str, tuple[Annotation, ...]]

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
    return MatrixRow(document, info.title or document.pdf_title or document.original_filename or "", info.year, citekey, resource_id, cells)


def _normalize_tag(tag: str | None) -> str:
    return (tag or "").strip().lstrip("#").strip().lower()


def make_matrix(rows: Iterable[MatrixRow], matrix_filter: MatrixFilter | None = None) -> Matrix:
    """Suzgeci uygular: sutunlari kisitlar, alintilari etikete gore eler, hicbir alintisi kalmayan satiri atar.
    Satirlar citekey sirasiyla (citekey'i olmayanlar sonda, basliga gore)."""
    flt = matrix_filter or MatrixFilter()
    all_columns = column_keys()
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
            kept.append(MatrixRow(row.document, row.title, row.year, row.citekey, row.resource_id, cells))
    kept.sort(key=lambda r: (r.citekey is None, r.citekey or "", r.title.casefold(), r.document.id))
    return Matrix(columns, tuple(kept))


# ---------------------------------------------------------------------- #
# Markdown
# ---------------------------------------------------------------------- #


def _cell_text(text: str) -> str:
    """Tablo hucresi icin guvenli metin: tek satir, `%%` etkisiz, `|` ve `<` `>` kacirilmis."""
    cleaned = inline_text(text).replace("\\", "\\\\")  # ters bolu once: yoksa `\|` kacisi bozulur
    return cleaned.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def _shorten(text: str) -> str:
    return text if len(text) <= MAX_QUOTE_LENGTH else text[: MAX_QUOTE_LENGTH - 1].rstrip() + "…"


def quote_markdown(document: Document, annotation: Annotation) -> str:
    """Hucredeki tek alinti: `• “alinti” ([s. 3](pkm://…)) — yorum`."""
    line = f"• “{_shorten(_cell_text(annotation.quote_exact))}”"
    if annotation.status != STATUS_ORPHANED and annotation.page is not None:
        line += f" ({page_link(document, annotation.page, annotation.uid)})"
    comment = _cell_text(annotation.comment or "")
    if comment:
        line += f" — {_shorten(comment)}"
    return line


def row_header(row: MatrixRow) -> str:
    title = _cell_text(row.title) or (row.citekey or "İsimsiz")
    year = f" ({row.year})" if row.year else ""
    return f"[[{row.citekey}]] · {title}{year}" if row.citekey else f"{title}{year}"


def column_name(key: str) -> str:
    return GENERAL_NAME if key == GENERAL_KEY else name_for_label(key)


def render_table(matrix: Matrix) -> list[str]:
    """Matrisin Markdown tablosu (satir listesi). Satir yoksa bos liste."""
    if not matrix.rows:
        return []
    header = ["Kaynak"] + [column_name(key) for key in matrix.columns]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for row in matrix.rows:
        cells = [
            CELL_SEPARATOR.join(quote_markdown(row.document, a) for a in row.cells.get(key, ()))
            for key in matrix.columns
        ]
        lines.append("| " + " | ".join([row_header(row)] + cells) + " |")
    return lines


def matrix_summary(matrix: Matrix) -> str:
    return f"{len(matrix.rows)} kaynak · {matrix.annotation_count} alıntı"


def render_markdown(matrix: Matrix, title: str = "Literatür Matrisi") -> str:
    """Disa aktarilacak tam Markdown (baslik + ozet + tablo). Satir yoksa yalniz baslik ve aciklama."""
    lines = [f"# {title}", ""]
    table = render_table(matrix)
    if not table:
        return "\n".join(lines + ["_Eşleşen alıntı yok._"]) + "\n"
    return "\n".join(lines + [f"_{matrix_summary(matrix)}_", ""] + table) + "\n"

