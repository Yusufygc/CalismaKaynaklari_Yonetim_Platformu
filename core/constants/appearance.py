"""Gorunum ayarlari: renk temasi ve yazi tipi cifti kimlikleri. Tanimlar QML tarafindadir
(`qml/theme/palettes.js`, `qml/theme/fonts.js`); buradaki listeler kaydedilen ayarin gecerliligini denetler ve
`tests/test_qml/test_appearance.py` ile QML listeleriyle esitligi sabitlenir."""

DEFAULT_PALETTE = "akademik-mavi"
PALETTE_IDS = (
    "akademik-mavi",
    "klasik-akademik",
    "modern-akademik",
    "kutuphane-vintage",
    "bilimsel-teknik",
    "prestijli-universite",
)

DEFAULT_FONT_PAIR = "varsayilan"
FONT_PAIR_IDS = (
    "varsayilan",
    "klasik-kitap",
    "tez-kapagi",
    "modern-sade",
    "prestijli",
    "bilimsel",
    "poster",
)

SETTING_PALETTE = "ui_palette"
SETTING_FONT_PAIR = "ui_font_pair"
SETTING_DARK = "ui_dark"
