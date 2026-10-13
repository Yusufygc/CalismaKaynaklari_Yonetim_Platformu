"""Tema motoru (qml/theme/palettes.js): her tema ve mod icin metin/zemin ciftleri WCAG AA olmali; renkler gecerli."""
import re
from pathlib import Path

import pytest
from PySide6.QtQml import QJSEngine

THEME_DIR = Path(__file__).resolve().parents[2] / "qml" / "theme"
HEX = re.compile(r"^#[0-9A-F]{6}$")


@pytest.fixture(scope="module")
def engine():
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    js = QJSEngine()
    source = (THEME_DIR / "palettes.js").read_text(encoding="utf-8").replace(".pragma library", "")
    result = js.evaluate(source)
    assert not result.isError(), result.toString()
    return js


def _ids(engine) -> list[str]:
    return engine.evaluate("ids()").toVariant()


def _tokens(engine, palette: str, dark: bool) -> dict:
    return engine.evaluate(f'build("{palette}", {str(dark).lower()})').toVariant()


def _contrast(engine, a: str, b: str) -> float:
    return engine.evaluate(f'contrast("{a}", "{b}")').toNumber()


def _cases():
    from core.constants.appearance import PALETTE_IDS

    return [(palette, dark) for palette in PALETTE_IDS for dark in (False, True)]


CASES = _cases()
CASE_IDS = [f"{palette}-{'koyu' if dark else 'acik'}" for palette, dark in CASES]
SURFACES = ["bgBase", "bgSidebar", "bgSurface", "bgElevated", "bgHover"]


@pytest.mark.parametrize(("palette", "dark"), CASES, ids=CASE_IDS)
def test_every_token_is_a_valid_hex_color(engine, palette, dark):
    tokens = _tokens(engine, palette, dark)
    bad = {name: value for name, value in tokens.items() if not HEX.match(str(value))}
    assert bad == {}


@pytest.mark.parametrize(("palette", "dark"), CASES, ids=CASE_IDS)
def test_text_is_readable_on_every_surface(engine, palette, dark):
    tokens = _tokens(engine, palette, dark)
    failures = []
    for text, minimum in (("textPrimary", 7.0), ("textSecondary", 4.5), ("textMuted", 4.5)):
        for surface in SURFACES:
            ratio = _contrast(engine, tokens[text], tokens[surface])
            if ratio < minimum:
                failures.append(f"{text} on {surface}: {ratio:.2f} < {minimum}")
    assert failures == []


@pytest.mark.parametrize(("palette", "dark"), CASES, ids=CASE_IDS)
def test_accent_status_and_action_pairs_are_readable(engine, palette, dark):
    tokens = _tokens(engine, palette, dark)
    pairs = [
        ("textOnAccent", "accent"),
        ("accentText", "accentSubtle"),
        ("accentText", "bgSidebar"),
        ("accentText", "bgSurface"),
        ("statusInbox", "statusInboxBg"),
        ("statusPlanned", "statusPlannedBg"),
        ("statusInProgress", "statusInProgressBg"),
        ("statusCompleted", "statusCompletedBg"),
        ("statusCompleted", "bgSurface"),
        ("statusInProgress", "bgSurface"),
        ("dangerText", "dangerSubtle"),
    ]
    failures = [
        f"{fg} on {bg}: {_contrast(engine, tokens[fg], tokens[bg]):.2f}"
        for fg, bg in pairs
        if _contrast(engine, tokens[fg], tokens[bg]) < 4.5
    ]
    assert failures == []


@pytest.mark.parametrize(("palette", "dark"), CASES, ids=CASE_IDS)
def test_surfaces_are_distinguishable_and_the_pin_is_visible(engine, palette, dark):
    tokens = _tokens(engine, palette, dark)
    assert tokens["bgBase"] != tokens["bgSurface"] != tokens["bgHover"]
    assert _contrast(engine, tokens["pin"], tokens["bgSurface"]) >= 3.0  # simge rengi: >= 3:1
    assert _contrast(engine, tokens["borderStrong"], tokens["bgSurface"]) >= 1.3  # kenarlik gorunur


def test_the_default_palette_matches_the_approved_academic_blue(engine):
    light = _tokens(engine, "akademik-mavi", False)
    assert light["bgBase"] == "#F4F1E9" and light["accent"] == "#1E4FA8" and light["textPrimary"].startswith("#")
