"""Tema paleti okunabilirlik denetimi: metin/zemin ciftleri her iki temada WCAG AA (>= 4.5:1) olmali."""
import re
from pathlib import Path

import pytest

THEME = Path(__file__).resolve().parents[2] / "qml" / "theme" / "Theme.qml"
_PAIR = re.compile(r'readonly property color (\w+): isDark \? "(#[0-9A-Fa-f]{6})(?:[0-9A-Fa-f]{2})?" : "(#[0-9A-Fa-f]{6})(?:[0-9A-Fa-f]{2})?"')
_SINGLE = re.compile(r'readonly property color (\w+): "(#[0-9A-Fa-f]{6})"')


def _palette(dark: bool) -> dict[str, str]:
    source = THEME.read_text(encoding="utf-8")
    colors = {name: (dark_value if dark else light_value) for name, dark_value, light_value in _PAIR.findall(source)}
    colors.update({name: value for name, value in _SINGLE.findall(source) if name not in colors})
    return colors


def _luminance(color: str) -> float:
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


SURFACES = ["bgBase", "bgSidebar", "bgSurface", "bgElevated", "bgHover"]


@pytest.mark.parametrize("dark", [True, False], ids=["koyu", "acik"])
def test_text_is_readable_on_every_surface(dark):
    colors = _palette(dark)
    failures = []
    for text, minimum in (("textPrimary", 7.0), ("textSecondary", 4.5), ("textMuted", 4.5)):
        for surface in SURFACES:
            ratio = contrast(colors[text], colors[surface])
            if ratio < minimum:
                failures.append(f"{text} on {surface}: {ratio:.2f} < {minimum}")
    assert failures == []


@pytest.mark.parametrize("dark", [True, False], ids=["koyu", "acik"])
def test_accent_status_and_action_pairs_are_readable(dark):
    colors = _palette(dark)
    pairs = [
        ("textOnAccent", "accent"),
        ("accentText", "accentSubtle"),
        ("accentText", "bgSidebar"),
        ("statusInbox", "statusInboxBg"),
        ("statusPlanned", "statusPlannedBg"),
        ("statusInProgress", "statusInProgressBg"),
        ("statusCompleted", "statusCompletedBg"),
        ("dangerText", "dangerSubtle"),
        ("statusCompleted", "bgSurface"),
        ("statusInProgress", "bgSurface"),
    ]
    failures = [f"{fg} on {bg}: {contrast(colors[fg], colors[bg]):.2f}" for fg, bg in pairs if contrast(colors[fg], colors[bg]) < 4.5]
    assert failures == []
