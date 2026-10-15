"""QML metinlerinde tema yazi tiplerinde bulunmayan simge yok: eksik glif Windows'ta eski bitmap yazi tiplerine
(Fixedsys, 8514oem) yedek arama yaptirir ve konsola `DirectWrite: CreateFontFaceFromHDC() failed` basar."""
from pathlib import Path

QML_DIR = Path(__file__).resolve().parents[2] / "qml"
TURKISH_AND_LATIN = set("çÇğĞıİöÖşŞüÜâîûÂÎÛ")
# Tum paketli/Windows tema yazi tiplerinde (Sitka, Segoe UI, Inter, Source Sans...) bulunduklari dogrulanan karakterler.
SAFE_SYMBOLS = set("·•…“”—–«»×")


def test_qml_sources_only_use_symbols_every_theme_font_has():
    offenders = []
    for path in QML_DIR.rglob("*"):
        if path.suffix not in {".qml", ".js"}:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for char in line:
                if ord(char) > 127 and char not in TURKISH_AND_LATIN and char not in SAFE_SYMBOLS:
                    offenders.append(f"{path.relative_to(QML_DIR)}:{number} U+{ord(char):04X}")
    assert offenders == []
