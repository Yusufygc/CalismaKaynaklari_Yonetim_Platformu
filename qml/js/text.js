.pragma library

// Turkce-duyarsiz arama katlamasi (utils/text_utils.py::fold_tr ile ayni kural):
// buyuk/kucuk harf ve diyakritik duyarsiz. JS toLowerCase() Turkce I/i'yi dogru katlamaz.
var _map = {
    "\u0130": "i", "I": "i", "\u0131": "i",
    "\u015e": "s", "\u015f": "s", "\u011e": "g", "\u011f": "g",
    "\u00dc": "u", "\u00fc": "u", "\u00d6": "o", "\u00f6": "o",
    "\u00c7": "c", "\u00e7": "c"
}

function foldTr(text) {
    if (!text) return ""
    let out = ""
    for (let i = 0; i < text.length; i++) {
        const ch = text[i]
        out += _map[ch] !== undefined ? _map[ch] : ch
    }
    return out.toLowerCase()
}
