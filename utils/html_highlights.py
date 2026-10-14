"""HTML makale metninde kayitli alintilari boyar (metin okuyucusu).

Alinti metni (`selectedText`) kayitli HTML'in gorunen metnidir. Burada HTML etiketlere ve metin parcalarina bolunur,
metin parcalari birlestirilip alintinin ilk eslesmesi aranir (etiketler gorunmez sayilir, yani baglanti/ust simge/vurgu
etiketleri araya girse de eslesir) ve eslesmenin kapsadigi her metin parcasinin ilgili kismi
`<span style="background-color:...">` ile sarilir. Birden cok paragrafa yayilan alinti paragraf basina ayri aranir.
Daha once boyanmis bolgeler engeldir: ayni metin tekrar secilirse siradaki eslesme boyanir. Eslesmeyen alinti (metin
sonradan degistiyse) sessizce atlanir; kayit silinmez. Renk yalnizca `#RRGGBB` kabul edilir (HTML'e baska bir sey sizmaz)."""
import html as html_lib
import re

_TAG = re.compile(r"(<[^>]*>)")
_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_PARAGRAPH_BREAKS = re.compile(r"[  \n\r]+")
_MIN_FRAGMENT = 3  # bundan kisa parcalar boyanmaz (tek harf/rakam yanlis yerde eslesir)
_MARK_TEXT_COLOR = "#14213D"  # sari/yesil zeminde koyu tema metni de okunsun
_BARRIER = "\x00"  # boyanmis bolge: eslesme bunun uzerinden gecemez

_TEXT, _TAG_KIND, _MARK = "text", "tag", "mark"


def _fragments(content: str) -> list[str]:
    return [part.strip() for part in _PARAGRAPH_BREAKS.split(content or "") if len(part.strip()) >= _MIN_FRAGMENT]


def _pattern(fragment: str) -> re.Pattern[str]:
    escaped = html_lib.escape(fragment, quote=False)
    return re.compile(r"\s+".join(re.escape(word) for word in escaped.split()))


def _tokenize(html: str) -> list[tuple[str, str]]:
    return [(_TAG_KIND if piece.startswith("<") else _TEXT, piece) for piece in _TAG.split(html) if piece]


def _mark_first_match(tokens: list[tuple[str, str]], pattern: re.Pattern[str], opening: str) -> bool:
    """`pattern`in tum metin parcalari uzerindeki ilk eslesmesini boyar; boyadiysa True."""
    joined_parts: list[str] = []
    spans: list[tuple[int, int, int]] = []  # (belirtec sirasi, birlesik metindeki baslangic, bitis)
    cursor = 0
    for index, (kind, piece) in enumerate(tokens):
        if kind == _TEXT:
            joined_parts.append(piece)
            spans.append((index, cursor, cursor + len(piece)))
            cursor += len(piece)
        elif kind == _MARK:
            joined_parts.append(_BARRIER)
            cursor += 1
    match = pattern.search("".join(joined_parts))
    if match is None:
        return False
    start, end = match.span()
    for index, begin, finish in reversed(spans):  # sondan basa: bolmeler onceki sira numaralarini bozmaz
        if finish <= start or begin >= end:
            continue
        piece = tokens[index][1]
        local_start, local_end = max(start, begin) - begin, min(end, finish) - begin
        tokens[index:index + 1] = [
            (_TEXT, piece[:local_start]),
            (_MARK, opening),
            (_MARK, piece[local_start:local_end]),
            (_MARK, "</span>"),
            (_TEXT, piece[local_end:]),
        ]
    return True


def apply_highlights(html: str, highlights: list[dict]) -> str:
    """`highlights`: [{content, color}]. Boyanmis HTML'i doner; boyanacak bir sey yoksa girdiyi degistirmez."""
    if not html or not highlights:
        return html
    tokens = _tokenize(html)
    changed = False
    for item in highlights:
        color = str(item.get("color") or "")
        if not _COLOR.match(color):
            continue
        opening = f'<span style="background-color:{color}; color:{_MARK_TEXT_COLOR};">'
        for fragment in _fragments(str(item.get("content") or "")):
            changed = _mark_first_match(tokens, _pattern(fragment), opening) or changed
    return "".join(piece for _kind, piece in tokens) if changed else html
