import re

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
