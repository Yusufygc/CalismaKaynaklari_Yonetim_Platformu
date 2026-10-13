"""Kutuphane geneli tam metin arama: sorgu kurucu ve ozet parcasi. Saf Python (veritabani ya da FTS bilmez).

Arama metni disaridan (kullanici girdisi) gelir ve FTS5 sozdizimi olarak YORUMLANMAZ: yalniz `\\w+` belirteclerinin
tirnakli birlesimi MATCH'e verilir; operator (`AND`, `NEAR`, `*`, `-`, `column:`) enjekte edilemez."""
import re
from dataclasses import dataclass

MAX_QUERY_TOKENS = 12
MAX_TOKEN_LENGTH = 64
SNIPPET_WIDTH = 160

_TOKEN = re.compile(r"\w+", re.UNICODE)
_QUOTED = re.compile(r'"([^"]*)"')
_TR_FOLD = str.maketrans({
    "İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s", "Ğ": "g", "ğ": "g",
    "Ü": "u", "ü": "u", "Ö": "o", "ö": "o", "Ç": "c", "ç": "c",
})


def fold(text: str | None) -> str:
    """Arama karsilastirmasi icin Turkce-duyarsiz normal form (`utils.text_utils.fold_tr` ile AYNI kural; testle
    sabitlenir). pdfkit uygulama katmanlarina bagimli olmasin diye burada ayrica tutulur."""
    return (text or "").translate(_TR_FOLD).casefold()


def tokens_of(text: str) -> list[str]:
    """Katlanmis `\\w+` belirtecleri (sinirli sayida/uzunlukta)."""
    found = [t[:MAX_TOKEN_LENGTH] for t in _TOKEN.findall(fold(text))]
    return found[:MAX_QUERY_TOKENS]


@dataclass(frozen=True)
class ParsedQuery:
    """`match`: FTS5 MATCH ifadesi; `terms`: ozet parcasinda vurgulanacak katlanmis belirtecler (son belirtec onektir)."""

    match: str
    terms: tuple[str, ...]
    prefix_last: bool


def parse_query(text: str | None) -> ParsedQuery | None:
    """Kullanici arama metnini guvenli MATCH ifadesine cevirir; aranacak bir sey yoksa None.

    - Bosluklu sozcukler hepsi gecmeli (AND).
    - `"tirnakli ifade"` ardisik sozcuk dizisi olarak aranir.
    - Son (tirnaksiz) sozcuk onektir: `kuant` -> `kuantum`... (yazarken arama)."""
    raw = text or ""
    parts: list[str] = []
    terms: list[str] = []
    budget = MAX_QUERY_TOKENS
    for phrase in _QUOTED.findall(raw):
        words = tokens_of(phrase)[:budget]
        if words:
            parts.append('"' + " ".join(words) + '"')
            terms.extend(words)
            budget -= len(words)
    loose = tokens_of(_QUOTED.sub(" ", raw))[: max(budget, 0)]
    prefix_last = bool(loose) and not raw.rstrip().endswith('"')
    for index, word in enumerate(loose):
        is_last = index == len(loose) - 1
        parts.append(f'"{word}"*' if is_last and prefix_last else f'"{word}"')
    terms.extend(loose)
    if not parts:
        return None
    return ParsedQuery(" ".join(parts), tuple(terms), prefix_last)


@dataclass(frozen=True)
class Snippet:
    """`text`: gosterilecek ozet; `spans`: vurgulanacak (baslangic, bitis) araliklari (`text` icinde)."""

    text: str
    spans: tuple[tuple[int, int], ...]


def make_snippet(original: str, query: ParsedQuery, width: int = SNIPPET_WIDTH) -> Snippet:
    """Sayfa metninden ilk eslesmenin cevresini keser. Eslesme KATLANMIS belirteclerle yapilir ama kesit OZGUN
    metinden alinir (buyuk/kucuk harf ve Turkce karakterler korunur)."""
    text = " ".join((original or "").split())
    if not text:
        return Snippet("", ())
    matches = _match_spans(text, query)
    if not matches:
        return Snippet(text[:width] + ("…" if len(text) > width else ""), ())
    first = matches[0][0]
    start = max(0, first - width // 3)
    end = min(len(text), start + width)
    start = max(0, end - width)
    if start > 0 and text[start - 1] != " ":  # sozcuk ortasindan baslamasin
        space = text.find(" ", start, first)
        start = space + 1 if space != -1 else start
    prefix, suffix = ("…" if start > 0 else ""), ("…" if end < len(text) else "")
    shown = prefix + text[start:end] + suffix
    shift = len(prefix) - start
    spans = tuple((a + shift, b + shift) for a, b in matches if a >= start and b <= end)
    return Snippet(shown, spans)


def _match_spans(text: str, query: ParsedQuery) -> list[tuple[int, int]]:
    spans = []
    last_term = len(query.terms) - 1
    for found in _TOKEN.finditer(text):
        word = fold(found.group())
        for index, term in enumerate(query.terms):
            prefix_term = query.prefix_last and index == last_term
            if word == term or (prefix_term and word.startswith(term)):
                spans.append((found.start(), found.end()))
                break
    return spans


@dataclass(frozen=True)
class SearchHit:
    """Bir sayfa eslesmesi. `page` 0 tabanli; `rank` kucuk = daha alakali (bm25)."""

    document_id: int
    page: int
    snippet: Snippet
    rank: float
