import re
import unicodedata

_STYLES = ("apa", "ieee", "bibtex")


def _split_name(full_name: str) -> tuple[str, list[str]]:
    """'Noam M. Shazeer' -> ('Shazeer', ['N', 'M'])."""
    parts = [p for p in full_name.replace(",", " ").split() if p]
    if not parts:
        return "", []
    if len(parts) == 1:
        return parts[0], []
    last = parts[-1]
    initials = [p[0].upper() for p in parts[:-1] if p[0].isalpha()]
    return last, initials


def _apa_author(name: str) -> str:
    last, initials = _split_name(name)
    return f"{last}, {' '.join(i + '.' for i in initials)}" if initials else last


def _ieee_author(name: str) -> str:
    last, initials = _split_name(name)
    return f"{' '.join(i + '.' for i in initials)} {last}".strip()


def _join_apa(authors: list[str]) -> str:
    formatted = [_apa_author(a) for a in authors]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) <= 20:
        return ", ".join(formatted[:-1]) + ", & " + formatted[-1]
    return ", ".join(formatted[:19]) + ", ... " + formatted[-1]


def _join_ieee(authors: list[str]) -> str:
    if len(authors) > 6:
        return f"{_ieee_author(authors[0])} et al."
    formatted = [_ieee_author(a) for a in authors]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    return ", ".join(formatted[:-1]) + ", and " + formatted[-1]


def _ascii_slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", normalized.lower())


_STOPWORDS = {"a", "an", "the", "of", "on", "in", "for", "and", "to", "with", "is", "are"}


def _bibtex_key(authors: list[str], year, title: str) -> str:
    last = _ascii_slug(_split_name(authors[0])[0]) if authors else "anon"
    first_word = next(
        (w for w in (_ascii_slug(t) for t in title.split()) if w and w not in _STOPWORDS), "untitled"
    )
    return f"{last}{year or 'nd'}{first_word}"


def _doi_url(doi: str) -> str:
    return doi if doi.startswith("http") else f"https://doi.org/{doi}"


class CitationService:
    """Kaynak metadata'sindan (extra_metadata) APA / IEEE / BibTeX atıf üretir.

    Beklenen anahtarlar (hepsi opsiyonel): title, authors (list[str]), year,
    venue, doi. Eksik alanlar atlanır; en azından başlık zorunludur.
    """

    @staticmethod
    def supported_styles() -> tuple[str, ...]:
        return _STYLES

    @classmethod
    def format(cls, title: str, metadata: dict, style: str) -> str:
        style = style.lower()
        if style not in _STYLES:
            raise ValueError(f"Desteklenmeyen atif stili: {style}")
        authors = [a for a in (metadata.get("authors") or []) if a]
        year = metadata.get("year")
        venue = (metadata.get("venue") or "").strip()
        doi = (metadata.get("doi") or "").strip()
        title = (title or metadata.get("title") or "").strip()
        return getattr(cls, f"_{style}")(title, authors, year, venue, doi)

    @staticmethod
    def _apa(title, authors, year, venue, doi) -> str:
        parts = []
        if authors:
            parts.append(_join_apa(authors))
        parts.append(f"({year})." if year else "(t.y.).")
        parts.append(f"{title}.")
        if venue:
            parts.append(f"{venue}.")
        if doi:
            parts.append(_doi_url(doi))
        return " ".join(parts)

    @staticmethod
    def _ieee(title, authors, year, venue, doi) -> str:
        head = f"{_join_ieee(authors)}, " if authors else ""
        text = f'{head}"{title},"'
        if venue:
            text += f" {venue},"
        if year:
            text += f" {year}"
        text = text.rstrip(",")
        if doi:
            text += f", doi: {doi.replace('https://doi.org/', '')}"
        return text + "."

    @staticmethod
    def _bibtex(title, authors, year, venue, doi) -> str:
        key = _bibtex_key(authors, year, title)
        fields = [f"  title = {{{{{title}}}}}"]
        if authors:
            bib_authors = []
            for name in authors:
                last, initials = _split_name(name)
                bib_authors.append(f"{last}, {' '.join(i + '.' for i in initials)}" if initials else last)
            fields.append(f"  author = {{{' and '.join(bib_authors)}}}")
        if year:
            fields.append(f"  year = {{{year}}}")
        if venue:
            fields.append(f"  journal = {{{venue}}}")
        if doi:
            fields.append(f"  doi = {{{doi.replace('https://doi.org/', '')}}}")
        return "@article{" + key + ",\n" + ",\n".join(fields) + "\n}"
