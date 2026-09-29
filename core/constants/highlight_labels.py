"""Highlight renklerinin akademik anlamları (etiketleri).

Renk paleti `qml/theme/Theme.qml::highlightPalette` ile aynı sırada/değerde
tutulmalıdır. Etiket, renkten türetilir (ayrı bir DB kolonu yok) -- böylece
bir alıntının rengi değiştirilince anlamı da tutarlı biçimde değişir.
"""

HIGHLIGHT_LABELS: list[dict[str, str]] = [
    {"color": "#EAB308", "label": "Önemli"},
    {"color": "#22C55E", "label": "Bulgu / Sonuç"},
    {"color": "#06B6D4", "label": "Yöntem"},
    {"color": "#A855F7", "label": "Tanım / Kavram"},
    {"color": "#EC4899", "label": "Eleştiri / Soru"},
]

_UNLABELED = "Genel"


def label_for_color(color: str | None) -> str:
    normalized = (color or "").strip().upper()
    for entry in HIGHLIGHT_LABELS:
        if entry["color"] == normalized:
            return entry["label"]
    return _UNLABELED
