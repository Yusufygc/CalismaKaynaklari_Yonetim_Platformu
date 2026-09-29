import re


def sanitize_utf8(text: str) -> str:
    """Gecersiz tek-basina UTF-16 surrogate kod noktalarini temizler.

    Bazi PDF'lerdeki bozuk/eksik CMap'e sahip subset fontlar (ozellikle
    matematik sembolleri iceren akademik makalelerde) pypdf/Qt metin
    cikariminda tek-basina surrogate kod noktalari (U+D800-DFFF) uretebiliyor.
    Bunlar gecerli Python str karakterleri ama gecerli UTF-8 degil --
    SQLite'a yazilirken `UnicodeEncodeError: surrogates not allowed` ile
    cokuyordu. Kaynagin (extraction) hemen sonrasinda temizlenir.
    """
    return text.encode("utf-8", errors="replace").decode("utf-8")


# Cümle sonu: . ! ? (ardından kapanış tırnağı/parantez olabilir) + boşluk + büyük harf/rakam/tırnak.
# "et al.", "Fig. 3", "e.g." gibi kısaltmalarda kırılmaması için sonraki karakter büyük harf şartı aranır
# ve bilinen kısaltmalar ayrıca elenir.
_BOUNDARY = re.compile(r"""[.!?]["')\]]?\s+(?=["'(\[]?[A-ZÇĞİÖŞÜ0-9])""")
_ABBREVIATIONS = ("et al.", "fig.", "eq.", "e.g.", "i.e.", "vs.", "cf.", "no.", "dr.", "prof.", "sec.")


def _is_real_boundary(text: str, match: re.Match) -> bool:
    prefix = text[max(0, match.start() - 6): match.start() + 1].lower()
    return not any(prefix.endswith(abbr) for abbr in _ABBREVIATIONS)


def extract_sentence(text: str, start: int, length: int, max_len: int = 400) -> str:
    """`text` içinde [start, start+length) aralığını kapsayan cümleyi döndürür.

    PDF metninde satır sonları (\\r\\n) cümlenin ortasına düşebildiği için
    sadece noktalama + sonraki büyük harf ile cümle sınırı aranır. Sonuç tek
    satıra normalize edilir ve `max_len` ile sınırlandırılır.
    """
    if not text or start < 0 or start >= len(text):
        return ""
    end = min(len(text), start + max(length, 1))

    sentence_start = 0
    for match in _BOUNDARY.finditer(text, 0, start):
        if _is_real_boundary(text, match):
            sentence_start = match.end()

    sentence_end = len(text)
    for match in _BOUNDARY.finditer(text, end):
        if _is_real_boundary(text, match):
            sentence_end = match.start() + 1
            break

    sentence = " ".join(text[sentence_start:sentence_end].split())
    if len(sentence) > max_len:
        sentence = sentence[:max_len].rstrip() + "…"
    return sentence


# Turkce arama katlamasi: buyuk/kucuk harf VE diyakritik duyarsiz ("Istanbul", "ISTANBUL",
# "İstanbul", "istanbul" hepsi ayni). `str.lower()`/SQLite `LIKE` Turkce I/İ/ı'yi dogru
# katlamaz ('İ'.lower() = 'i̇', 'I'.lower() = 'i' ama Turkcede 'ı').
_TR_FOLD = str.maketrans(
    {
        "İ": "i", "I": "i", "ı": "i",
        "Ş": "s", "ş": "s",
        "Ğ": "g", "ğ": "g",
        "Ü": "u", "ü": "u",
        "Ö": "o", "ö": "o",
        "Ç": "c", "ç": "c",
    }
)


def fold_tr(text: str | None) -> str:
    """Arama karsilastirmasi icin Turkce-duyarsiz normal form (i/ı/İ/I -> i, ş->s, ğ->g, ü->u, ö->o, ç->c)."""
    if not text:
        return ""
    return text.translate(_TR_FOLD).casefold()
