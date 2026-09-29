"""Testler icin deterministik, metin iceren kucuk PDF'ler uretir (harici dosya/kutuphane gerekmez)."""
from pathlib import Path

DEFAULT_LINES = [
    "Birinci cumle burada biter. Hizli kahverengi tilki tembel kopegin ustunden atlar. Ucuncu cumle.",
    "Ikinci satir baska bir paragrafin baslangicidir. Son cumle burada.",
]


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_text_pdf(lines: list[str] | None = None) -> bytes:
    """Tek sayfalik (612x792), Helvetica 14pt, her `lines` ogesi ayri satir olan gecerli bir PDF."""
    lines = lines or DEFAULT_LINES
    content = ["BT", "/F1 14 Tf", "72 700 Td", "20 TL"]
    for i, line in enumerate(lines):
        content.append(f"({_escape(line)}) Tj" if i == 0 else f"T* ({_escape(line)}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)


def write_text_pdf(path: Path, lines: list[str] | None = None) -> Path:
    path.write_bytes(build_text_pdf(lines))
    return path


def write_outline_pdf(path: Path, titles: list[str]) -> Path:
    """Her baslik icin bir sayfa + ust duzey anahat (yer imi) ogesi iceren PDF (pypdf ile)."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in titles:
        writer.add_blank_page(width=300, height=400)
    for page_number, title in enumerate(titles):
        writer.add_outline_item(title, page_number)
    with open(path, "wb") as handle:
        writer.write(handle)
    return path
