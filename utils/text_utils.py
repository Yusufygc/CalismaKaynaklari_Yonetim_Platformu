from pdfkit.domain.sentences import extract_sentence  # noqa: F401  (geriye uyumluluk; Faz 8'de kalkar)


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
