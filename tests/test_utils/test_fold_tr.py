from pathlib import Path

import pytest
from PySide6.QtQml import QJSEngine

from utils.text_utils import fold_tr

SAMPLES = ["İstanbul", "ISPARTA", "ısparta", "Şeker Çiçeği", "Öğrenme ve Öğretme", "ÜĞÜR", "abc XYZ", "Ünlü", ""]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("İstanbul", "istanbul"),
        ("ISPARTA", "isparta"),
        ("ısparta", "isparta"),
        ("Şeker", "seker"),
        ("ÇĞÖÜ çğöü", "cgou cgou"),
        (None, ""),
        ("", ""),
    ],
)
def test_fold_tr(text, expected):
    assert fold_tr(text) == expected


def test_turkish_variants_fold_to_same_key():
    assert fold_tr("Isparta") == fold_tr("ısparta") == fold_tr("İSPARTA") == fold_tr("isparta")


def test_qml_js_fold_matches_python_fold():
    """qml/js/text.js ile utils/text_utils.fold_tr ayni kurali uygulamali (arama sonuclari tutarli olsun)."""
    js_path = Path(__file__).resolve().parents[2] / "qml" / "js" / "text.js"
    source = js_path.read_text(encoding="utf-8").replace(".pragma library", "")
    engine = QJSEngine()
    result = engine.evaluate(source + "\n(function(t) { return foldTr(t) })")
    assert result.isCallable()

    for sample in SAMPLES:
        assert result.call([engine.toScriptValue(sample)]).toString() == fold_tr(sample), sample
