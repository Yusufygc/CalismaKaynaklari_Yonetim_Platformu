"""Alinti capasi cozumleyici (W3C TextQuote + TextPosition yaklasimi).

Bir alinti `Segment` (Qt PDFium metin indeksi araligi) + metin (`quote_exact`, onceki/sonraki baglam) ile saklanir.
Cozumleme sirasi: (1) kayitli konumdaki metin alintiyla uyusuyor mu; (2) ayni sayfada bosluk-normalize
arama (onceki/sonraki baglamla ayristirma); (3) ayni sayfada harf-rakam disindakileri yok sayan arama
(satir sonu tirelemesi, ligatur bosluklari); (4) komsu sayfalar; (5) bulunamazsa `orphaned`. Alinti sessizce
kaybolmaz. Saf Python: PDF'e `PageTextProvider` uzerinden erisilir.
"""
from dataclasses import dataclass, replace
from typing import Protocol

from pdfkit.domain.annotations import STATUS_OK, STATUS_ORPHANED, Segment

CONTEXT_CHARS = 32
_MIN_QUOTE_CHARS = 3  # Daha kisa alintilarda arama sahte eslesme uretir; yalniz konum dogrulanir.
_NEIGHBOR_PAGES = (-1, 1)


class PageTextProvider(Protocol):
    def page_count(self) -> int: ...

    def text_of(self, page: int) -> str:
        """Sayfanin Qt PDFium metni (alinti indeksleriyle ayni indeks uzayi)."""


@dataclass(frozen=True)
class Resolution:
    status: str  # STATUS_OK | STATUS_ORPHANED
    segments: list[Segment]
    method: str | None  # "position" | "context" | "squash" | "neighbor" | None
    moved: bool  # konum kayitli konumdan farkli mi
    prefix: str | None = None  # cozumlenen ilk parcanin onundeki baglam
    suffix: str | None = None  # cozumlenen son parcanin ardindaki baglam


class _Normalized:
    """Normalize edilmis metin + normalize indeks -> orijinal indeks haritasi."""

    def __init__(self, text: str, squash: bool) -> None:
        chars: list[str] = []
        index_map: list[int] = []
        previous_space = True  # bastaki bosluklar atilir
        for position, char in enumerate(text):
            if squash:
                if not char.isalnum():
                    continue
                for piece in char.casefold():
                    chars.append(piece)
                    index_map.append(position)
            elif char.isspace():
                if not previous_space:
                    chars.append(" ")
                    index_map.append(position)
                previous_space = True
            else:
                chars.append(char)
                index_map.append(position)
                previous_space = False
        if not squash and chars and chars[-1] == " ":
            chars.pop()
            index_map.pop()
        self.text = "".join(chars)
        self.index_map = index_map

    def occurrences(self, needle: str) -> list[int]:
        found, start = [], self.text.find(needle)
        while start != -1:
            found.append(start)
            start = self.text.find(needle, start + 1)
        return found

    def original_range(self, norm_start: int, norm_length: int) -> tuple[int, int]:
        return self.index_map[norm_start], self.index_map[norm_start + norm_length - 1] + 1


def normalize_ws(text: str) -> str:
    return _Normalized(text, squash=False).text


def _common_suffix(a: str, b: str) -> int:
    count = 0
    while count < min(len(a), len(b)) and a[-1 - count] == b[-1 - count]:
        count += 1
    return count


def _common_prefix(a: str, b: str) -> int:
    count = 0
    while count < min(len(a), len(b)) and a[count] == b[count]:
        count += 1
    return count


def _pick(
    normalized: _Normalized, needle: str, prefix: str, suffix: str, hint_start: int
) -> tuple[int, int] | None:
    """Adaylar arasindan baglama en cok uyani (esitlikte kayitli konuma en yakin olani) secer."""
    candidates = normalized.occurrences(needle)
    if not candidates:
        return None
    best, best_key = None, None
    for start in candidates:
        # Baglamlar kenar bosluklari atilmis saklanir; adayin komsu metni de ayni bicime getirilir.
        before = normalized.text[max(0, start - len(prefix) - 1) : start].rstrip()
        after = normalized.text[start + len(needle) : start + len(needle) + len(suffix) + 1].lstrip()
        score = (_common_suffix(before, prefix) if prefix else 0) + (_common_prefix(after, suffix) if suffix else 0)
        distance = abs(normalized.index_map[start] - hint_start)
        key = (-score, distance)
        if best_key is None or key < best_key:
            best, best_key = start, key
    return normalized.original_range(best, len(needle))


def _search_page(
    text: str, quote: str, prefix: str | None, suffix: str | None, hint_start: int
) -> tuple[tuple[int, int], str] | None:
    for squash, method in ((False, "context"), (True, "squash")):
        needle = _Normalized(quote, squash).text
        if len(needle) < _MIN_QUOTE_CHARS:
            return None
        normalized = _Normalized(text, squash)
        found = _pick(
            normalized,
            needle,
            _Normalized(prefix or "", squash).text,
            _Normalized(suffix or "", squash).text,
            hint_start,
        )
        if found:
            return found, method
    return None


def _context(text: str, start: int, end: int) -> tuple[str, str]:
    return text[max(0, start - CONTEXT_CHARS) : start], text[end : end + CONTEXT_CHARS]


def _resolve_segment(
    segment: Segment, provider: PageTextProvider, prefix: str | None, suffix: str | None
) -> tuple[Segment, str] | None:
    quote = segment.text
    pages = [segment.page] + [segment.page + delta for delta in _NEIGHBOR_PAGES]
    for page in pages:
        if page < 0 or page >= provider.page_count():
            continue
        text = provider.text_of(page)
        if page == segment.page and 0 <= segment.start < segment.end <= len(text):
            if normalize_ws(text[segment.start : segment.end]) == normalize_ws(quote):
                return segment, "position"
        found = _search_page(text, quote, prefix, suffix, segment.start if page == segment.page else 0)
        if found:
            (start, end), method = found
            return replace(segment, page=page, start=start, end=end, polygons=None), (
                method if page == segment.page else "neighbor"
            )
    return None


def resolve(
    segments: list[Segment], prefix: str | None, suffix: str | None, provider: PageTextProvider
) -> Resolution:
    """Alintinin parcalarini gecerli PDF metninde yeniden konumlandirir. Her parca ayri cozumlenir; birinin
    bile bulunamamasi alintiyi `orphaned` yapar (kismen dogru konum gostermek yaniltici olur)."""
    resolved: list[Segment] = []
    methods: list[str] = []
    for index, segment in enumerate(segments):
        outcome = _resolve_segment(
            segment, provider, prefix if index == 0 else None, suffix if index == len(segments) - 1 else None
        )
        if outcome is None:
            return Resolution(STATUS_ORPHANED, list(segments), None, moved=False)
        resolved.append(outcome[0])
        methods.append(outcome[1])
    moved = resolved != segments
    method = next((m for m in methods if m != "position"), "position")
    first, last = resolved[0], resolved[-1]
    before, _ = _context(provider.text_of(first.page), first.start, first.end)
    _, after = _context(provider.text_of(last.page), last.start, last.end)
    return Resolution(STATUS_OK, resolved, method, moved, prefix=before, suffix=after)
