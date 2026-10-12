"""Obsidian vault notu: belge basina `Papers/<citekey>.md`. Saf Python (dosya ya da veritabani bilmez).

Not iki parcadir: (1) uygulamanin yonettigi frontmatter anahtarlari ve (2) sentinel'li uretilen blok
(`%% pkm:begin ... %%` ile `%% pkm:end ... %%` arasi). Dosyadaki diger her sey kullanicinindir ve birlestirmede
**oldugu gibi korunur**: yonetilmeyen frontmatter satirlari, bloktan once/sonra yazilan metin, satir sonu bicimi.

`compose_note(mevcut, icerik)` idempotenttir: ayni icerikle iki kez calistirmak metni degistirmez."""
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass

from pdfkit.domain.annotations import STATUS_ORPHANED, Annotation, PageNote, Term
from pdfkit.domain.deeplink import build_open_link
from pdfkit.domain.errors import VaultNoteError
from pdfkit.domain.labels import GENERAL_KEY, is_known_label, name_for_label
from pdfkit.domain.models import Document, SourceInfo

BEGIN_MARKER = "%% pkm:begin annotations"
SENTINEL_BEGIN = BEGIN_MARKER + " — bu bloğun içi uygulama tarafından yazılır %%"
SENTINEL_END = "%% pkm:end annotations %%"
MANAGED_KEYS = ("pkm_id", "citekey", "title", "authors", "year", "doi", "status")
NOTE_DIRECTORY = "Papers"
_BLOCK_ID_LENGTH = 8
_NO_PAGE_SORT = 10**6
_KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*)\s*:")


@dataclass(frozen=True)
class NoteContent:
    """Bir belge icin notun ihtiyac duydugu her sey."""

    document: Document
    info: SourceInfo
    citekey: str
    annotations: Sequence[Annotation] = ()
    notes: Sequence[PageNote] = ()
    terms: Sequence[Term] = ()


def note_rel_path(citekey: str) -> str:
    """Vault kokune gore not yolu ('/' ayiracli). Citekey yalnizca [a-z0-9] oldugundan yol enjeksiyonu yoktur."""
    if not re.fullmatch(r"[a-z0-9]{1,80}", citekey):
        raise VaultNoteError(f"Geçersiz citekey: {citekey!r}")
    return f"{NOTE_DIRECTORY}/{citekey}.md"


def block_id(prefix: str, uid: str) -> str:
    """Obsidian blok kimligi: `hl-8f3a2c1d` (alinti), `nt-...` (not). ULID'nin rastgele kuyrugundan turetilir."""
    return f"{prefix}-{uid[-_BLOCK_ID_LENGTH:].lower()}"


# ---------------------------------------------------------------------- #
# Metin temizligi
# ---------------------------------------------------------------------- #


def _no_comment_markers(text: str) -> str:
    """Kullanici metnindeki `%%` Obsidian yorum isaretcisidir; sentinel'i bozmasin diye bolunur."""
    return text.replace("%%", "% %")


def inline_text(text: str) -> str:
    return _no_comment_markers(" ".join((text or "").split()))


def _lines(text: str) -> list[str]:
    lines = [line.rstrip() for line in _no_comment_markers((text or "").replace("\r\n", "\n").replace("\r", "\n")).split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def obsidian_tag(tag: str) -> str:
    """Serbest etiketi Obsidian etiketine cevirir: bosluk '-', yalnizca harf/rakam/_/-//. Bos ya da yalniz
    rakamlardan olusan etiket Obsidian'da etiket sayilmaz: bos dizge doner."""
    cleaned = re.sub(r"[^\w\-/]", "", re.sub(r"\s+", "-", (tag or "").strip().lstrip("#")), flags=re.UNICODE)
    return "" if not cleaned or cleaned.isdigit() else cleaned


# ---------------------------------------------------------------------- #
# Uretilen blok
# ---------------------------------------------------------------------- #


def _page_link(document: Document, page: int, uid: str) -> str:
    return f"[s. {page + 1}]({build_open_link(document.sha256, page, uid)})"


def _callout_type(label_key: str) -> str:
    return label_key if is_known_label(label_key) and label_key != GENERAL_KEY else "note"


def _annotation_lines(document: Document, annotation: Annotation) -> list[str]:
    label = name_for_label(annotation.label_key)
    if annotation.status == STATUS_ORPHANED or annotation.page is None:
        heading = f"> [!{_callout_type(annotation.label_key)}] {label} · konumu bulunamadı"
    else:
        heading = f"> [!{_callout_type(annotation.label_key)}] {label} · {_page_link(document, annotation.page, annotation.uid)}"
    body = [f"> “{inline_text(annotation.quote_exact)}”"]
    comment = _lines(annotation.comment or "")
    if comment:
        body += [">", f"> **Yorum:** {comment[0]}"] + [f"> {line}" for line in comment[1:]]
    tags = [t for t in (obsidian_tag(t) for t in annotation.tags) if t]
    if tags:
        body += [">", "> " + " ".join(f"#{t}" for t in tags)]
    body[-1] += f" ^{block_id('hl', annotation.uid)}"
    return [heading] + body


def _note_lines(document: Document, note: PageNote) -> list[str]:
    text = _lines(note.text) or [""]
    lines = [f"> [!note] Not · {_page_link(document, note.page, note.uid)}"] + [f"> {line}" for line in text]
    lines[-1] += f" ^{block_id('nt', note.uid)}"
    return lines


def term_line(document: Document, term: Term) -> str:
    line = f"- **{inline_text(term.word)}** — {inline_text(term.translation)}"
    if term.segments:
        line += f" · {_page_link(document, term.segments[0].page, term.uid)}"
    if term.context_sentence:
        line += f" — _“{inline_text(term.context_sentence)}”_"
    return line


def _annotation_sort_key(annotation: Annotation) -> tuple:
    first = annotation.segments[0] if annotation.segments else None
    orphan = annotation.status == STATUS_ORPHANED or first is None
    return (orphan, _NO_PAGE_SORT if orphan else first.page, 0 if orphan else first.start, annotation.id)


def render_block(content: NoteContent) -> str:
    """Sentinel'ler dahil uretilen blok (satir sonu `\\n`, sonda bos satir yok)."""
    document = content.document
    sections: list[list[str]] = []
    annotations = sorted(content.annotations, key=_annotation_sort_key)
    if annotations:
        items = [_annotation_lines(document, a) for a in annotations]
        sections.append(["### Alıntılar", ""] + _join_blank(items))
    notes = sorted(content.notes, key=lambda n: (n.page, n.id))
    if notes:
        sections.append(["### Notlar", ""] + _join_blank([_note_lines(document, n) for n in notes]))
    terms = sorted(content.terms, key=lambda t: (t.segments[0].page if t.segments else _NO_PAGE_SORT, t.word.lower(), t.id))
    if terms:
        sections.append(["### Kelimeler", ""] + [term_line(document, t) for t in terms])
    lines = [SENTINEL_BEGIN, ""]
    if sections:
        lines += _join_blank(sections)
    else:
        lines.append("_Henüz alıntı, not ya da kelime yok._")
    lines += ["", SENTINEL_END]
    return "\n".join(lines)


def _join_blank(groups: list[list[str]]) -> list[str]:
    joined: list[str] = []
    for index, group in enumerate(groups):
        if index:
            joined.append("")
        joined += group
    return joined


# ---------------------------------------------------------------------- #
# Frontmatter
# ---------------------------------------------------------------------- #


def _yaml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)  # JSON dizgesi gecerli bir YAML cift tirnakli dizgedir


def managed_fields(content: NoteContent) -> dict[str, str]:
    """Uygulamanin yonettigi frontmatter anahtarlari ve YAML degerleri; degeri olmayanlar atlanir."""
    info = content.info
    fields = {
        "pkm_id": content.document.sha256[:16],
        "citekey": _yaml(content.citekey),
        "title": _yaml(inline_text(info.title)) if info.title else "",
        "authors": "[" + ", ".join(_yaml(inline_text(a)) for a in info.authors if a.strip()) + "]" if info.authors else "",
        "year": str(info.year) if info.year else "",
        "doi": _yaml(info.doi) if info.doi else "",
        "status": _yaml(info.status) if info.status else "",
    }
    return {key: value for key, value in fields.items() if value}


def _split_frontmatter(text: str) -> tuple[list[str], str] | None:
    """(frontmatter satirlari, geri kalan metin) ya da frontmatter yoksa None; kapanmamissa hata."""
    if not text.startswith("---\n"):
        return None
    lines = text.split("\n")
    for index in range(1, len(lines)):
        if lines[index].rstrip() == "---":
            return lines[1:index], "\n".join(lines[index + 1:])
    raise VaultNoteError("Frontmatter kapanmamış ('---' eksik); dosyaya dokunulmadı.")


def _entries(lines: list[str]) -> list[tuple[str | None, list[str]]]:
    """Frontmatter satirlarini (anahtar, satirlar) girdilerine boler; ust duzey olmayan satirlar oncekine aittir."""
    entries: list[tuple[str | None, list[str]]] = []
    for line in lines:
        match = _KEY_LINE.match(line)
        if match:
            entries.append((match.group(1), [line]))
        elif entries:
            entries[-1][1].append(line)
        else:
            entries.append((None, [line]))
    return entries


def _merge_frontmatter(lines: list[str], fields: dict[str, str]) -> list[str]:
    merged: list[str] = []
    written: set[str] = set()
    for key, entry_lines in _entries(lines):
        if key in fields:
            merged.append(f"{key}: {fields[key]}")
            written.add(key)
        else:
            merged.extend(entry_lines)
    for key in MANAGED_KEYS:
        if key in fields and key not in written:
            merged.append(f"{key}: {fields[key]}")
    return merged


# ---------------------------------------------------------------------- #
# Birlestirme
# ---------------------------------------------------------------------- #


def replace_block(text: str, block: str, begin_marker: str = BEGIN_MARKER, end_marker: str = SENTINEL_END) -> str:
    """Sentinel'li blogu degistirir; hic sentinel yoksa blogu sona ekler. Eksik, tekrarli ya da ters sentinel
    kullanici metnine dokunulamayacagi anlamina gelir: `VaultNoteError`."""
    lines = text.split("\n")
    begins = [i for i, line in enumerate(lines) if line.strip().startswith(begin_marker)]
    ends = [i for i, line in enumerate(lines) if line.strip() == end_marker]
    if not begins and not ends:
        return text.rstrip("\n") + "\n\n" + block + "\n"
    if len(begins) != 1 or len(ends) != 1 or begins[0] > ends[0]:
        raise VaultNoteError("Sentinel işaretleri bozuk (eksik, tekrarlı ya da ters); dosyaya dokunulmadı.")
    merged = lines[: begins[0]] + block.split("\n") + lines[ends[0] + 1:]
    return "\n".join(merged)


def compose_note(existing: str | None, content: NoteContent) -> str:
    """Notun yeni metnini uretir. `existing` None/bos ise yeni not; degilse kullanici metni korunarak birlestirilir.

    Kullanici metnine dokunulamayacaksa (bozuk sentinel, kapanmamis frontmatter) `VaultNoteError` firlatir ve
    cagiran dosyaya yazmaz."""
    block = render_block(content)
    fields = managed_fields(content)
    if existing is None or not existing.strip():
        return _new_note(content, fields, block)
    newline = "\r\n" if "\r\n" in existing else "\n"
    text = existing.replace("\r\n", "\n")
    split = _split_frontmatter(text)
    if split is None:
        header = _merge_frontmatter([], fields)
        text = "---\n" + "\n".join(header) + "\n---\n\n" + text
    else:
        header, rest = split
        text = "---\n" + "\n".join(_merge_frontmatter(header, fields)) + "\n---" + ("\n" + rest if rest or text.endswith("\n") else "")
    text = replace_block(text, block)
    if not text.endswith("\n"):
        text += "\n"
    return text.replace("\n", newline) if newline != "\n" else text


def _new_note(content: NoteContent, fields: dict[str, str], block: str) -> str:
    header = _merge_frontmatter([], fields) + ["tags: [paper]"]
    title = inline_text(content.info.title) or content.citekey
    return "---\n" + "\n".join(header) + "\n---\n\n" + f"# {title}\n\n" + block + "\n"
