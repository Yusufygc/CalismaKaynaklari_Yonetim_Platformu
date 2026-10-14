"""PDF sayfa metnini okunur paragraflara cevirir (metin okuyucusu icin).

PDFium sayfa metnini satir satir verir (baski genisligindeki satir kirilimlari, tireli sozcuk bolmeleri, ust/alt bilgi
satirlari dahil). Tum sayfayi tek paragrafa katmak okunmaz sonuc verir; burada yalniz metinden cikarilabilen
sezgiler uygulanir (sutun/konum bilgisi yoktur):

- satir sonu tirelemesi birlestirilir ("firma-" + "nin" -> "firmanin"),
- tekrar eden ust/alt bilgi satirlari ve yalin sayfa numaralari atilir,
- kisa, cumle sonu noktalamasiyla biten satirdan sonra yeni paragraf baslar,
- numarali/buyuk harfli kisa satirlar baslik olur.

Saf Python; PDF ya da Qt bilmez."""
import re
from collections import Counter
from dataclasses import dataclass

_LINE_SPLIT = re.compile(r"\r\n|\r|\n")
_PAGE_NUMBER = re.compile(r"^(?:sayfa|page|s\.)?\s*\d{1,4}(?:\s*/\s*\d{1,4})?$", re.IGNORECASE)
_NUMBERED_HEADING = re.compile(r"^(?:\d+(?:\.\d+){0,3}\.?|[IVX]{1,5}\.)\s+\S")
_SENTENCE_END = (".", "!", "?", ":", "”", '"', "…", ")")
_KNOWN_HEADINGS = {
    "özet", "abstract", "giriş", "introduction", "sonuç", "sonuçlar", "conclusion", "conclusions", "kaynakça", "kaynaklar",
    "references", "yöntem", "yöntemler", "methods", "method", "tartışma", "discussion", "bulgular", "results", "teşekkür",
    "anahtar kelimeler", "keywords",
}
_HEADER_CANDIDATES = 2  # sayfanin ilk ve son bu kadar satiri ust/alt bilgi adayidir
_MAX_HEADING_LENGTH = 90


@dataclass(frozen=True)
class Block:
    """`kind`: 'p' (paragraf) ya da 'h' (baslik)."""

    kind: str
    text: str


def _fingerprint(line: str) -> str:
    """Ust/alt bilgi karsilastirma anahtari: rakamlar ve bosluk farklari yok sayilir ("Nisan 2021, 16 (1) 3" ~ "... 4")."""
    return re.sub(r"\d+", "#", " ".join(line.lower().split()))


def _clean_lines(raw: str) -> list[str]:
    return [" ".join(line.split()) for line in _LINE_SPLIT.split(raw or "")]


def _edge_lines(visible: list[str]) -> list[str]:
    """Ust/alt bilgi adayi satirlar: sayfanin ilk ve son satirlari. Kisa sayfalarda (< 7 satir) aday yoktur: orada her satir
    gercek metin olabilir."""
    if len(visible) < 2 * _HEADER_CANDIDATES + 3:
        return []
    return visible[:_HEADER_CANDIDATES] + visible[-_HEADER_CANDIDATES:]


def repeated_lines(pages: list[str]) -> set[str]:
    """Birden cok sayfanin basinda/sonunda tekrar eden (ust/alt bilgi) satirlarin parmak izleri. Az sayfada (< 4) hicbir
    sey tekrar sayilmaz: gercek metin yanlislikla atilmasin."""
    if len(pages) < 4:
        return set()
    counts: Counter[str] = Counter()
    for raw in pages:
        edge = _edge_lines([line for line in _clean_lines(raw) if line])
        counts.update({_fingerprint(line) for line in edge if len(line) >= 4})
    threshold = max(3, int(len(pages) * 0.35))
    return {key for key, count in counts.items() if count >= threshold}


def _is_upper_heading(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 4 and sum(c.isupper() for c in letters) / len(letters) > 0.85


def _is_heading(line: str) -> bool:
    if not line or len(line) > _MAX_HEADING_LENGTH or line.endswith((".", ",", ";", ":", "!", "?")) and not _NUMBERED_HEADING.match(line):
        return False
    if line.lower().rstrip(":") in _KNOWN_HEADINGS:
        return True
    if _NUMBERED_HEADING.match(line):
        words = line.split()
        return len(words) <= 12 and not line.rstrip().endswith((",", ";"))
    return _is_upper_heading(line)


def _join(previous: str, line: str) -> str:
    """Iki satiri birlestirir; satir sonu tirelemesinde ("firma-" + "nin") tire atilir."""
    if previous.endswith("-") and len(previous) > 1 and previous[-2].isalnum():
        if previous[-2].isalpha() and line[:1].islower():
            return previous[:-1] + line  # bolunmus sozcuk: "firma-" + "nin"
        if line[:1].isalnum():
            return previous + line  # gercek tire ("ARIMA-" + "DVM", "2010-" + "2019"): tire kalir, bosluk girmez
    return previous + " " + line


def reflow_page(raw: str, header_footer: set[str] | None = None) -> list[Block]:
    """Tek sayfanin metnini paragraf/baslik bloklarina cevirir."""
    skip = header_footer or set()
    lines = [line for line in _clean_lines(raw)]
    visible = [line for line in lines if line]
    edge = set(_edge_lines(visible))
    kept: list[str] = []
    for line in lines:
        if not line:
            kept.append("")  # bos satir: paragraf siniri
        elif _PAGE_NUMBER.match(line) or (line in edge and _fingerprint(line) in skip):
            continue
        else:
            kept.append(line)

    lengths = sorted(len(line) for line in kept if len(line) >= 20)
    full = lengths[int(len(lengths) * 0.8)] if lengths else 0  # "dolu satir" uzunlugu

    blocks: list[Block] = []
    current = ""
    previous_length = 0  # bir onceki FIZIKSEL satirin uzunlugu (paragraf sonu: cumle sonu + kisa satir)

    def flush() -> None:
        nonlocal current
        if current:
            blocks.append(Block("p", current))
        current = ""

    for line in kept:
        if not line:
            flush()
            previous_length = 0
            continue
        ends_paragraph = bool(current) and current.endswith(_SENTENCE_END) and full > 0 and previous_length < full * 0.75
        if _is_heading(line) and (not current or ends_paragraph or current.endswith(_SENTENCE_END)):
            flush()
            blocks.append(Block("h", line))
            previous_length = 0
            continue
        if ends_paragraph:
            flush()
        current = _join(current, line) if current else line
        previous_length = len(line)
    flush()
    return blocks


def reflow_pages_html(pages: list[str], escape) -> str:
    """Sayfa metinlerini `<h3>Sayfa N</h3>` + paragraflar/basliklar (`<p>`, `<h4>`) HTML'ine cevirir. `escape` HTML kacirma
    islevidir. Bos sayfalar atlanir; hic metin yoksa bos dizge."""
    skip = repeated_lines(pages)
    parts: list[str] = []
    for number, raw in enumerate(pages, start=1):
        blocks = reflow_page(raw, skip)
        if not blocks:
            continue
        body = "".join(
            f"<h4>{escape(block.text)}</h4>" if block.kind == "h" else f"<p>{escape(block.text)}</p>" for block in blocks
        )
        parts.append(f"<h3>Sayfa {number}</h3>{body}")
    return "".join(parts)
