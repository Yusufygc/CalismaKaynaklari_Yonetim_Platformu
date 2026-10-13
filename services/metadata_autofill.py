"""Kunye (yazar, yil, dergi, DOI...) otomatik doldurma kurallari. Saf; agi, veritabanini ya da Qt'yi bilmez.

Ilke: otomatik doldurma kullanicinin elle girdigi/duzelttigi hicbir degeri EZMEZ; yalniz bos alanlari doldurur.
(Elle "Akademik bilgi getir" duzgunce yeniden yazar; bu yol sessizce, arka planda calisir.)"""
import re

from utils.text_utils import fold_tr

# `source` (kaynagin ice aktarma kokeni: local_pdf, web...) ve diger anahtarlar asla otomatik doldurulmaz.
FILLABLE_KEYS = ("authors", "year", "venue", "doi", "openalex_id", "citation_count")

_MIN_TOKEN = 3
_MIN_TOKENS_TO_JUDGE = 2
_MIN_OVERLAP = 0.5


def _empty(value) -> bool:
    return value in (None, "", [], ())


def fill_missing(existing: dict | None, incoming: dict | None) -> tuple[dict, list[str]]:
    """`existing`'in kopyasini, yalniz bos izin verilen alanlari `incoming`'den doldurarak dondurur; ikinci deger
    doldurulan anahtarlardir (bos liste = degisiklik yok)."""
    merged = dict(existing or {})
    added = []
    for key in FILLABLE_KEYS:
        value = (incoming or {}).get(key)
        if _empty(value) or not _empty(merged.get(key)):
            continue
        merged[key] = value
        added.append(key)
    return merged, added


def _tokens(title: str | None) -> set[str]:
    return {t for t in re.findall(r"\w+", fold_tr(title or "")) if len(t) >= _MIN_TOKEN}


def titles_conflict(pdf_title: str | None, found_title: str | None) -> bool:
    """Bulunan makale PDF'in KENDI gomulu basligiyla acikca celisiyor mu? PDF'ten cikarilan DOI bazen metindeki bir
    ATIF yapilan makaleye aittir; o zaman yanlis makalenin kunyesi (ve basligi) sessizce yazilmasin.

    Yalniz gomulu baslik varsa ve iki tarafin da yargilanacak kadar (>= 2) anlamli sozcugu varsa karar verilir;
    aksi halde (gomulu baslik yok, dosya adi gibi guvenilmez ya da cok kisa) celiski sayilmaz. Olcut: kisa basligin
    anlamli sozcuklerinin yarisindan azi uzun basliktakilerle ortusuyorsa celiski vardir."""
    first, second = _tokens(pdf_title), _tokens(found_title)
    if len(first) < _MIN_TOKENS_TO_JUDGE or len(second) < _MIN_TOKENS_TO_JUDGE:
        return False
    return len(first & second) / min(len(first), len(second)) < _MIN_OVERLAP
