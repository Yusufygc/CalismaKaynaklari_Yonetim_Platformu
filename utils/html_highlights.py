"""HTML makale metninde kayitli alintilari boyar (metin okuyucusu).

Alinti metni (`selectedText`) kayitli HTML'in gorunen metnidir; burada her alintinin ilk eslesmesi, etiketler arasindaki
metin parcalari icinde aranir ve `<span style="background-color:...">` ile sarilir. Birden cok paragrafa yayilan alinti
satir/paragraf basina ayri boyanir. Eslesmeyen alinti (metin sonradan degistiyse) sessizce atlanir; kayit silinmez.
Renk yalnizca `#RRGGBB` kabul edilir (HTML'e baska bir sey sizmaz)."""
import html as html_lib
import re

_TAG = re.compile(r"(<[^>]*>)")
_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_PARAGRAPH_BREAKS = re.compile(r"[  \n\r]+")
_MIN_FRAGMENT = 3  # bundan kisa parcalar boyanmaz (tek harf/rakam yanlis yerde eslesir)
_MARK_TEXT_COLOR = "#14213D"  # sari/yesil zeminde koyu tema metni de okunsun


def _fragments(content: str) -> list[str]:
    return [part.strip() for part in _PARAGRAPH_BREAKS.split(content or "") if len(part.strip()) >= _MIN_FRAGMENT]


def _pattern(fragment: str) -> re.Pattern[str]:
    escaped = html_lib.escape(fragment, quote=False)
    return re.compile(r"\s+".join(re.escape(word) for word in escaped.split()))


def apply_highlights(html: str, highlights: list[dict]) -> str:
    """`highlights`: [{content, color}]. Boyanmis HTML'i doner; boyanacak bir sey yoksa girdiyi degistirmez."""
    if not html or not highlights:
        return html
    tokens = [(not piece.startswith("<"), piece) for piece in _TAG.split(html) if piece]  # (aranabilir metin mi, parca)
    changed = False
    for item in highlights:
        color = str(item.get("color") or "")
        if not _COLOR.match(color):
            continue
        opening = f'<span style="background-color:{color}; color:{_MARK_TEXT_COLOR};">'
        for fragment in _fragments(str(item.get("content") or "")):
            pattern = _pattern(fragment)
            for index, (searchable, piece) in enumerate(tokens):
                if not searchable:
                    continue
                match = pattern.search(piece)
                if match is None:
                    continue
                tokens[index:index + 1] = [
                    (True, piece[:match.start()]),
                    (False, opening),
                    (False, piece[match.start():match.end()]),
                    (False, "</span>"),
                    (True, piece[match.end():]),
                ]
                changed = True
                break
    return "".join(piece for _searchable, piece in tokens) if changed else html
