import re
from pathlib import Path

from pkm_app.core.constants.colors import Colors
from pkm_app.core.themes.dark import DARK_THEME
from pkm_app.core.themes.light import LIGHT_THEME
from pkm_app.models import Category, Resource, ResourceStatus, Tag
from pkm_app.core.constants.status import status_label
from pkm_app.ui.components.category_row import CategoryRow
from pkm_app.ui.components.painted import ColorBadge, ColorSwatch
from pkm_app.ui.components.resource_card import ResourceCard
from pkm_app.ui.components.sidebar import Sidebar
from pkm_app.ui.components.url_rich_card import UrlRichCard
from pkm_app.core.events import event_bus
from pkm_app.ui.components.resource_detail_panel import ResourceDetailPanel


ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"
STYLE_DIR = ROOT / "assets" / "styles"


def _read_sources(path: Path, pattern: str) -> list[Path]:
    return sorted(path.rglob(pattern))


def test_ui_code_has_no_inline_stylesheet_calls():
    offenders = [
        file
        for file in _read_sources(UI_DIR, "*.py")
        if "setStyleSheet(" in file.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_ui_code_does_not_hardcode_hex_colors():
    hex_re = re.compile(r"#[0-9A-Fa-f]{6}\b")
    offenders = {
        file.name: hex_re.findall(file.read_text(encoding="utf-8"))
        for file in _read_sources(UI_DIR, "*.py")
        if hex_re.search(file.read_text(encoding="utf-8"))
    }

    assert offenders == {}


def test_qss_files_do_not_contain_hardcoded_hex_colors():
    hex_re = re.compile(r"#[0-9A-Fa-f]{3,8}")
    offenders = {
        file.name: hex_re.findall(file.read_text(encoding="utf-8"))
        for file in _read_sources(STYLE_DIR, "*.qss")
        if hex_re.search(file.read_text(encoding="utf-8"))
    }

    assert offenders == {}


def test_qss_files_do_not_append_alpha_to_theme_tokens():
    alpha_token_re = re.compile(r"\{\{[a-z_]+\}\}[0-9A-Fa-f]{2}")
    offenders = {
        file.name: alpha_token_re.findall(file.read_text(encoding="utf-8"))
        for file in _read_sources(STYLE_DIR, "*.qss")
        if alpha_token_re.search(file.read_text(encoding="utf-8"))
    }

    assert offenders == {}


def test_qtawesome_icons_do_not_use_literal_hex_colors():
    icon_re = re.compile(r"qta\.icon\([^)]*color\s*=\s*['\"]#")
    offenders = [
        file
        for file in _read_sources(UI_DIR, "*.py")
        if icon_re.search(file.read_text(encoding="utf-8"))
    ]

    assert offenders == []


def test_ui_code_does_not_use_numeric_qfont_weights():
    weight_re = re.compile(r"\.setWeight\(\s*\d+")
    offenders = [
        file
        for file in _read_sources(UI_DIR, "*.py")
        if weight_re.search(file.read_text(encoding="utf-8"))
    ]

    assert offenders == []


def test_theme_token_sets_match():
    assert set(DARK_THEME) == set(LIGHT_THEME)


def test_painted_widgets_and_cards_smoke(qapp):
    category = Category(name="Python", color_hex="#3776AB", icon="fa5s.folder")
    tag = Tag(name="docs")
    resource = Resource(
        title="Docs",
        status=ResourceStatus.PLANNED,
        priority=2,
        category=category,
        tags=[tag],
        extra_metadata={},
    )

    widgets = [
        ResourceCard(resource),
        UrlRichCard(resource),
        CategoryRow(category),
        Sidebar(),
        ColorSwatch("#3776AB", Colors.THEMES["dark"][Colors.CATEGORY_FALLBACK], Colors.THEMES["dark"][Colors.SWATCH_BORDER]),
        ColorSwatch("not-a-color", Colors.THEMES["dark"][Colors.CATEGORY_FALLBACK], Colors.THEMES["dark"][Colors.SWATCH_BORDER]),
    ]

    for widget in widgets:
        widget.show()
        assert widget.sizeHint().isValid()
        if isinstance(widget, (ResourceCard, UrlRichCard)):
            widget.setHoverProgress(1.0)
            widget.setHoverProgress(0.0)

    event_bus.theme_changed.emit(Colors.THEMES["light"])

    sidebar = next(widget for widget in widgets if isinstance(widget, Sidebar))
    for index in range(sidebar._nav_list.count()):
        assert not sidebar._nav_list.item(index).icon().isNull()

    for widget in widgets:
        widget.deleteLater()


def test_detail_view_status_options_are_turkish(qapp):
    panel = ResourceDetailPanel()

    labels = [
        panel._status_combo.itemText(index)
        for index in range(panel._status_combo.count())
    ]

    assert labels == [status_label(status) for status in ResourceStatus]
    panel.deleteLater()


def test_resource_card_shows_content_description(qapp):
    resource = Resource(
        title="Docs",
        status=ResourceStatus.PLANNED,
        priority=2,
        content="akademide ornek kullanim sunuyor",
        extra_metadata={},
    )

    card = ResourceCard(resource)

    assert card._description_label is not None
    assert card._description_label.text() == "akademide ornek kullanim sunuyor"
    card.deleteLater()


def test_url_rich_card_uses_content_as_description_fallback(qapp):
    resource = Resource(
        title="Video",
        url="https://youtu.be/abc123",
        status=ResourceStatus.PLANNED,
        priority=2,
        content="video aciklamasi",
        extra_metadata={},
    )

    card = UrlRichCard(resource)

    assert card._desc_label is not None
    assert card._desc_label.text() == "video aciklamasi"
    assert card.width() >= 300
    assert card.height() >= 360
    card.deleteLater()


def test_color_badge_interprets_css_alpha_hex_as_rgba(qapp):
    badge = ColorBadge("Planlandi", "#2563EB", "#2563EB22")

    assert badge._background.red() == 37
    assert badge._background.green() == 99
    assert badge._background.blue() == 235
    assert badge._background.alpha() == 34
    badge.deleteLater()
