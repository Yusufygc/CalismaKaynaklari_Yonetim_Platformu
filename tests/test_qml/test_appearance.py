"""Ayarlar > Gorunum: tema/yazi tipi kimlikleri, kalicilik, gecerlilik ve gercek QML etkilesimi."""
from pathlib import Path

import pytest
from PySide6.QtQml import QJSEngine
from PySide6.QtTest import QTest

from core.constants.appearance import (
    DEFAULT_FONT_PAIR,
    DEFAULT_PALETTE,
    FONT_PAIR_IDS,
    PALETTE_IDS,
    SETTING_DARK,
    SETTING_FONT_PAIR,
    SETTING_PALETTE,
)
from tests.test_qml.qml_harness import click, find_item, find_named, open_window, pump, walk
from ui_qml.bridge import QmlBridge

THEME_DIR = Path(__file__).resolve().parents[2] / "qml" / "theme"


def _js(name: str, qapp) -> QJSEngine:
    engine = QJSEngine()
    result = engine.evaluate((THEME_DIR / name).read_text(encoding="utf-8").replace(".pragma library", ""))
    assert not result.isError(), result.toString()
    return engine


def test_python_and_qml_theme_lists_are_identical(qapp):
    assert tuple(_js("palettes.js", qapp).evaluate("ids()").toVariant()) == PALETTE_IDS
    assert tuple(_js("fonts.js", qapp).evaluate("ids()").toVariant()) == FONT_PAIR_IDS
    assert _js("palettes.js", qapp).evaluate("defaultId").toString() == DEFAULT_PALETTE
    assert _js("fonts.js", qapp).evaluate("defaultId").toString() == DEFAULT_FONT_PAIR


def test_every_palette_has_five_swatches_a_name_and_a_description(qapp):
    engine = _js("palettes.js", qapp)
    palettes = engine.evaluate("palettes").toVariant()
    assert len(palettes) >= 6
    for palette in palettes:
        assert palette["name"] and palette["description"] and len(palette["swatches"]) == 5
        assert all(len(c) == 7 and c.startswith("#") for c in palette["swatches"] + [palette["primary"], palette["accent"], palette["paper"], palette["ink"]])


def test_fonts_resolve_to_the_first_installed_candidate_and_fall_back_to_the_last(qapp):
    engine = _js("fonts.js", qapp)

    def resolve(pair, available):
        names = ", ".join(f'"{n}"' for n in available)
        return engine.evaluate(f'resolve("{pair}", [{names}])').toVariant()

    full = resolve("klasik-kitap", ["EB Garamond", "Lato", "Georgia", "Segoe UI"])
    assert (full["heading"], full["body"], full["reading"]) == ("EB Garamond", "Lato", "EB Garamond")
    assert full["installed"] == {"heading": True, "body": True, "reading": True}

    windows = resolve("klasik-kitap", ["Garamond", "Candara", "Georgia", "Segoe UI"])
    assert (windows["heading"], windows["body"], windows["reading"]) == ("Garamond", "Candara", "Garamond")
    assert windows["installed"]["heading"] is False  # EB Garamond yok: benzeri kullaniliyor

    nothing = resolve("modern-sade", [])  # hic yazi tipi bilinmiyorsa son aday (Segoe UI)
    assert nothing["body"] == "Segoe UI" and nothing["heading"] == "Segoe UI"
    assert resolve("bilinmeyen", ["Sitka Heading"])["heading"] == "Sitka Heading"  # bilinmeyen kimlik varsayilana duser


@pytest.fixture()
def bridge(qapp, session):
    return QmlBridge(session)


def test_choices_default_validate_and_persist(bridge, qapp, session):
    appearance = bridge.appearance
    assert appearance.paletteId == DEFAULT_PALETTE and appearance.fontPairId == DEFAULT_FONT_PAIR
    changes = []
    appearance.paletteChanged.connect(lambda: changes.append("palette"))
    appearance.fontPairChanged.connect(lambda: changes.append("font"))

    appearance.setPalette("klasik-akademik")
    appearance.setFontPair("tez-kapagi")
    appearance.setPalette("klasik-akademik")  # ayni secim: sinyal yok
    appearance.setPalette("uydurma")  # gecersiz: yok sayilir
    appearance.setFontPair("")

    assert appearance.paletteId == "klasik-akademik" and appearance.fontPairId == "tez-kapagi" and changes == ["palette", "font"]
    settings = bridge.ctx.user_settings
    assert settings.get(SETTING_PALETTE) == "klasik-akademik" and settings.get(SETTING_FONT_PAIR) == "tez-kapagi"
    assert QmlBridge(session).appearance.paletteId == "klasik-akademik"  # sonraki acilista hatirlanir

    appearance.reset()
    assert appearance.paletteId == DEFAULT_PALETTE and appearance.fontPairId == DEFAULT_FONT_PAIR


def test_corrupt_stored_values_fall_back_to_defaults(qapp, session):
    first = QmlBridge(session)
    first.ctx.user_settings.set(SETTING_PALETTE, "silinmis-tema")
    first.ctx.user_settings.set(SETTING_FONT_PAIR, 42)

    again = QmlBridge(session)

    assert again.appearance.paletteId == DEFAULT_PALETTE and again.appearance.fontPairId == DEFAULT_FONT_PAIR


def test_light_dark_mode_is_remembered(qapp, session):
    first = QmlBridge(session)
    assert first.isDarkTheme is True  # varsayilan koyu (onceki davranis)
    first.toggleTheme()
    assert first.ctx.user_settings.get(SETTING_DARK) is False

    assert QmlBridge(session).isDarkTheme is False
    first.toggleTheme()
    assert QmlBridge(session).isDarkTheme is True


def _open_tab(qapp, bridge):
    engine, window = open_window(qapp, bridge, "settings", width=1300, height=900)
    click(qapp, window, find_named(window, "appearanceTab"))
    pump(qapp, 20)
    return engine, window


def _visible(window, name):
    return [i for i in walk(window.contentItem()) if i.objectName() == name and i.isVisible()]


def test_the_settings_tab_lists_themes_and_font_pairs_and_applies_a_clicked_choice(bridge, qapp):
    engine, window = _open_tab(qapp, bridge)
    palette_cards, font_cards = _visible(window, "paletteCard"), _visible(window, "fontCard")
    assert len(palette_cards) == len(PALETTE_IDS) and len(font_cards) == len(FONT_PAIR_IDS)
    before = window.property("color").name()

    click(qapp, window, palette_cards[1])  # Klasik Akademik
    pump(qapp, 20)
    assert bridge.appearance.paletteId == PALETTE_IDS[1]
    assert window.property("color").name() != before  # Theme.bgBase pencereye yansidi

    flick = find_item(window, lambda i: i.property("contentY") is not None and i.property("contentHeight") > window.height())
    flick.setProperty("contentY", flick.property("contentHeight") - flick.height())  # yazi tipi kartlari sayfanin altinda
    pump(qapp, 10)
    click(qapp, window, _visible(window, "fontCard")[2])
    pump(qapp, 10)
    assert bridge.appearance.fontPairId == FONT_PAIR_IDS[2]
    assert "Kullanılan:" in find_item(window, lambda i: i.objectName() == "fontCardInfo").property("text")

    click(qapp, window, find_named(window, "resetAppearanceButton"))
    pump(qapp, 10)
    assert bridge.appearance.fontPairId == DEFAULT_FONT_PAIR and bridge.appearance.paletteId == DEFAULT_PALETTE and window.property("color").name() == before
    assert engine.captured_warnings == []


def test_mode_buttons_switch_between_light_and_dark(bridge, qapp):
    engine, window = _open_tab(qapp, bridge)
    assert bridge.isDarkTheme is True

    click(qapp, window, find_named(window, "lightModeButton"))
    pump(qapp, 10)
    assert bridge.isDarkTheme is False
    click(qapp, window, find_named(window, "darkModeButton"))
    pump(qapp, 10)
    assert bridge.isDarkTheme is True and engine.captured_warnings == []
