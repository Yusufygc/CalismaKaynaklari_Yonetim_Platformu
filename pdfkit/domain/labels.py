from dataclasses import dataclass


@dataclass(frozen=True)
class Label:
    key: str
    name: str  # kullaniciya gorunen ad
    color: str  # varsayilan renk (tema paletiyle ayni)


# Anlam etiketleri birinci sinif alandir; renk etiketten turetilir (tersi degil). Palet
# `qml/theme/Theme.qml::highlightPalette` ile ayni degerlerdedir.
LABELS: tuple[Label, ...] = (
    Label("important", "Önemli", "#EAB308"),
    Label("finding", "Bulgu / Sonuç", "#22C55E"),
    Label("method", "Yöntem", "#06B6D4"),
    Label("concept", "Tanım / Kavram", "#A855F7"),
    Label("critique", "Eleştiri / Soru", "#EC4899"),
)
GENERAL_KEY = "general"
GENERAL_NAME = "Genel"
_BY_KEY = {label.key: label for label in LABELS}
_BY_COLOR = {label.color: label for label in LABELS}


def label_key_for_color(color: str | None) -> str:
    """Eski renk-tabanli alintilarin anlam etiketi; paletle eslesmeyen renk 'general'."""
    found = _BY_COLOR.get((color or "").strip().upper())
    return found.key if found else GENERAL_KEY


def color_for_label(key: str) -> str | None:
    label = _BY_KEY.get(key)
    return label.color if label else None


def name_for_label(key: str) -> str:
    label = _BY_KEY.get(key)
    return label.name if label else GENERAL_NAME


def is_known_label(key: str) -> bool:
    return key in _BY_KEY or key == GENERAL_KEY
