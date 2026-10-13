"""Vault'taki ozet notlari: kutuphane dizini (`Papers/_Index.md`) ve kelime defteri (`Papers/_Kelimeler.md`).

Belge notlarindan (`vault_note`) farki: tek dosyada tum belgeler bulunur ve frontmatter yonetilmez. Dosyanin tamami
degil, yalniz sentinel'li blogun ici uygulamanindir; blogun disindaki her sey kullanicinin olarak oldugu gibi korunur.
Dosya adlari sabittir (`_` ile baslar), citekey `[a-z0-9]` oldugundan hicbir belge notuyla cakismaz.

Blok yalnizca veriden uretilir (zaman damgasi yoktur): veri degismediyse `compose_summary` ayni metni dondurur ve
yazici dosyaya dokunmaz."""
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from pdfkit.domain.annotations import Term
from pdfkit.domain.models import Document
from pdfkit.domain.synthesis import MatrixFilter, MatrixOptions, MatrixRow, build_row, make_matrix, matrix_summary, render_table
from pdfkit.domain.vault_note import NOTE_DIRECTORY, NoteContent, inline_text, replace_block, term_line

INDEX_FILE = "_Index.md"
VOCABULARY_FILE = "_Kelimeler.md"
MATRIX_FILE = "_Matris.md"
_MAX_LISTED_AUTHORS = 3
_NO_PAGE_SORT = 10**6


def _markers(kind: str) -> tuple[str, str, str]:
    """(baslangic isaretcisi, tam baslangic satiri, bitis satiri)."""
    begin = f"%% pkm:begin {kind}"
    return begin, f"{begin} — bu bloğun içi uygulama tarafından yazılır %%", f"%% pkm:end {kind} %%"


@dataclass(frozen=True)
class IndexEntry:
    """Dizinde bir belge: not dosyasi (`citekey`), kunye ve icerik sayilari."""

    citekey: str
    title: str
    authors: tuple[str, ...] = ()
    year: int | None = None
    status: str = ""
    highlights: int = 0
    notes: int = 0
    terms: int = 0


@dataclass(frozen=True)
class VocabularySection:
    """Kelime defterinde bir belgenin kelimeleri."""

    document: Document
    citekey: str
    title: str
    terms: Sequence[Term]


def index_entry_for(content: NoteContent) -> IndexEntry:
    info = content.info
    return IndexEntry(
        citekey=content.citekey,
        title=info.title,
        authors=tuple(info.authors),
        year=info.year,
        status=info.status,
        highlights=len(content.annotations),
        notes=len(content.notes),
        terms=len(content.terms),
    )


def matrix_row_for(content: NoteContent) -> MatrixRow:
    return build_row(content.document, content.info, content.citekey, content.annotations)


def vocabulary_section_for(content: NoteContent) -> VocabularySection:
    return VocabularySection(content.document, content.citekey, content.info.title, tuple(content.terms))


def _entry_line(entry: IndexEntry) -> str:
    parts = [inline_text(entry.title) or entry.citekey]
    authors = [inline_text(a) for a in entry.authors if a.strip()]
    if authors:
        parts.append(", ".join(authors[:_MAX_LISTED_AUTHORS]) + (" vd." if len(authors) > _MAX_LISTED_AUTHORS else ""))
    if entry.year:
        parts.append(str(entry.year))
    counts = [
        f"{count} {name}" for count, name in ((entry.highlights, "alıntı"), (entry.notes, "not"), (entry.terms, "kelime")) if count
    ]
    parts.append(", ".join(counts) if counts else "henüz not yok")
    if entry.status:
        parts.append(inline_text(entry.status))
    return f"- [[{entry.citekey}]] — " + " · ".join(parts)


@dataclass(frozen=True)
class IndexContent:
    """Kutuphane dizini: bagli her belge icin bir satir (citekey sirasiyla)."""

    kind: ClassVar[str] = "index"
    filename: ClassVar[str] = INDEX_FILE
    title: ClassVar[str] = "Kütüphane Dizini"

    entries: Sequence[IndexEntry] = ()

    @property
    def is_empty(self) -> bool:
        return not self.entries

    def body_lines(self) -> list[str]:
        if not self.entries:
            return ["_Henüz kaynak yok._"]
        entries = sorted(self.entries, key=lambda e: e.citekey)
        return [f"### Kaynaklar ({len(entries)})", ""] + [_entry_line(e) for e in entries]


@dataclass(frozen=True)
class VocabularyContent:
    """Kelime defteri: kelimesi olan her belge icin bir bolum (citekey sirasiyla, kelimeler alfabetik)."""

    kind: ClassVar[str] = "vocabulary"
    filename: ClassVar[str] = VOCABULARY_FILE
    title: ClassVar[str] = "Kelime Defteri"

    sections: Sequence[VocabularySection] = ()

    @property
    def is_empty(self) -> bool:
        return not any(section.terms for section in self.sections)

    def body_lines(self) -> list[str]:
        sections = sorted((s for s in self.sections if s.terms), key=lambda s: s.citekey)
        if not sections:
            return ["_Henüz kelime yok._"]
        lines: list[str] = []
        for index, section in enumerate(sections):
            if index:
                lines.append("")
            lines += [f"### [[{section.citekey}]] — {inline_text(section.title) or section.citekey} ({len(section.terms)})", ""]
            ordered = sorted(section.terms, key=lambda t: (t.word.casefold(), t.id))
            lines += [term_line(section.document, term) for term in ordered]
        return lines


@dataclass(frozen=True)
class MatrixContent:
    """Literatur matrisi (kaynak x anlam etiketi). Hangi sutunlarin, hangi sirayla ve hucre basina kac alintinin yazilacagi
    kullanici ayarindan gelir (`options`); baska suzgec yoktur. Suzgecli cikti arayuzden disa aktarilir."""

    kind: ClassVar[str] = "matrix"
    filename: ClassVar[str] = MATRIX_FILE
    title: ClassVar[str] = "Literatür Matrisi"

    rows: Sequence[MatrixRow] = ()
    options: MatrixOptions = MatrixOptions()

    def _matrix(self):
        columns = self.options.vault_columns
        return make_matrix(self.rows, MatrixFilter(labels=columns) if columns is not None else None, order=self.options.order)

    @property
    def is_empty(self) -> bool:
        return not self._matrix().rows

    def body_lines(self) -> list[str]:
        matrix = self._matrix()
        if not matrix.rows:
            return ["_Henüz alıntı yok._"]
        return [f"_{matrix_summary(matrix)}_", ""] + render_table(matrix, self.options.cell_limit)


SummaryContent = IndexContent | VocabularyContent | MatrixContent


def summary_rel_path(content: SummaryContent) -> str:
    return f"{NOTE_DIRECTORY}/{content.filename}"


def render_summary_block(content: SummaryContent) -> str:
    _begin, begin_line, end_line = _markers(content.kind)
    return "\n".join([begin_line, "", *content.body_lines(), "", end_line])


def compose_summary(existing: str | None, content: SummaryContent) -> str:
    """Ozet notunun yeni metni. Dosya yoksa/bossa baslikla olusturulur; varsa yalniz sentinel'li blok degisir, kullanici
    metni ve satir sonu bicimi korunur. Sentinel bozuksa `VaultNoteError` (dosyaya dokunulmaz)."""
    block = render_summary_block(content)
    if existing is None or not existing.strip():
        header = f"---\npkm_kind: {json.dumps(content.kind)}\n---\n\n# {content.title}\n\n"
        return header + block + "\n"
    begin, _line, end = _markers(content.kind)
    newline = "\r\n" if "\r\n" in existing else "\n"
    text = replace_block(existing.replace("\r\n", "\n"), block, begin, end)
    if not text.endswith("\n"):
        text += "\n"
    return text.replace("\n", newline) if newline != "\n" else text
