"""Atif anahtari (citekey): not dosya adi ve Obsidian baglantilari icin kararli, ASCII, kisa kimlik.

Bicim: `<ilk yazar soyadi><yil><ilk anlamli baslik sozcugu>`, ornegin `lecun2015deep`. Cakismada `a`, `b`, ... eklenir.
Anahtar ilk atamada saklanir ve sonradan degismez (bkz. pdfkit/app/vault.py)."""
import re
import unicodedata
from collections.abc import Iterable

_TRANSLITERATION = str.maketrans(
    {"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ç": "c", "Ç": "c", "ö": "o", "Ö": "o",
     "ü": "u", "Ü": "u", "ß": "ss", "ø": "o", "Ø": "o", "đ": "d", "Đ": "d", "ł": "l", "Ł": "l", "æ": "ae", "œ": "oe"}
)
# Baslikta atlanan sik sozcukler (Ingilizce + Turkce); anahtar anlamli ilk sozcuktan uretilir.
_STOPWORDS = frozenset(
    "a an the of on in for and or to with without is are was from by at as into using use via towards toward "
    "ve ile bir bu su icin uzerine uzerinde de da ki mi ne gibi ya".split()
)
_MAX_SURNAME = 20
_MAX_KEYWORD = 12
_ANONYMOUS = "anon"
_NO_YEAR = "nd"
_YEAR = re.compile(r"(?<!\d)(1[5-9]\d\d|20\d\d|21\d\d)(?!\d)")


def ascii_slug(text: str) -> str:
    """Kucuk harfli, yalnizca [a-z0-9] iceren dizge (Turkce ve aksanli harfler karsiliklarina cevrilir)."""
    folded = unicodedata.normalize("NFKD", (text or "").translate(_TRANSLITERATION))
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in folded if not unicodedata.combining(c)).lower())


def surname_of(author: str) -> str:
    """'Y. LeCun' -> 'lecun'; 'LeCun, Yann' -> 'lecun'. Bulunamazsa bos dizge."""
    name = (author or "").strip()
    if not name:
        return ""
    if "," in name:
        name = name.split(",", 1)[0]
    else:
        name = name.split()[-1]
    return ascii_slug(name)[:_MAX_SURNAME]


def year_of(year: int | str | None) -> str:
    match = _YEAR.search(str(year)) if year is not None else None
    return match.group(1) if match else _NO_YEAR


def keyword_of(title: str) -> str:
    """Basligin ilk anlamli sozcugu (en az 3 karakter, durak sozcuk degil); yoksa bos dizge."""
    for token in re.findall(r"[^\W_]+", (title or "").translate(_TRANSLITERATION), flags=re.UNICODE):
        slug = ascii_slug(token)
        if len(slug) >= 3 and slug not in _STOPWORDS:
            return slug[:_MAX_KEYWORD]
    return ""


def base_citekey(authors: Iterable[str], year: int | str | None, title: str, fallback_author: str | None = None) -> str:
    """Cakisma ayrimi yapilmamis anahtar. Yazar yoksa `fallback_author` (PDF yazari), o da yoksa 'anon'."""
    surname = next((s for s in (surname_of(a) for a in authors) if s), "")
    if not surname and fallback_author:
        surname = surname_of(fallback_author.split(";")[0].split(" and ")[0])
    return f"{surname or _ANONYMOUS}{year_of(year)}{keyword_of(title)}"


def make_unique(base: str, taken: Iterable[str]) -> str:
    """`base` kullanilmissa `a`, `b`, ..., `z`, `aa`, ... son ekiyle ilk bos olani dondurur."""
    used = set(taken)
    if base not in used:
        return base
    suffix = 0
    while True:
        suffix += 1
        letters, number = "", suffix
        while number:
            number, remainder = divmod(number - 1, 26)
            letters = chr(ord("a") + remainder) + letters
        if base + letters not in used:
            return base + letters
