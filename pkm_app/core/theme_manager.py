from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

from core.constants.colors import Colors
from core.logger import log
from core.paths import resource_path, user_data_dir

if TYPE_CHECKING:
    pass

_STYLES_DIR = resource_path("assets", "styles")
_ICONS_DIR = resource_path("assets", "icons")
_COMBO_ARROW_PATH = user_data_dir() / "cache" / "combo_arrow.svg"


def _write_themed_svg(svg_name: str, color_hex: str, out_path) -> None:
    """`currentColor` icerikli bir SVG'yi verilen renkle boyayip diske yazar.

    QSS `url()` yalnizca dosya yolu kabul eder (QIcon degil) -- bu yuzden
    QComboBox ok ikonu gibi QSS'ten referans verilen ikonlar icin
    `ui/theme_utils.py::load_theme_svg`'deki boyama mantigi burada diske
    yazilabilir sekilde tekrarlanir (core katmani ui'a bagimli olmasin diye
    ayri tutuldu).
    """
    svg_path = _ICONS_DIR / svg_name
    if not svg_path.exists():
        return
    try:
        content = svg_path.read_text(encoding="utf-8")
        colored_content = content.replace("currentColor", color_hex)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(colored_content, encoding="utf-8")
    except OSError as exc:
        log.error("Tema ikonu yazilamadi: %s — %s", out_path, exc)


class _ThemeManager:
    """Singleton tema yoneticisi.

    QSS sablonlarindaki {{ anahtar }} yer tutucularini aktif temanin
    renkleriyle doldurur ve QApplication'a uygular.
    """

    _instance: "_ThemeManager | None" = None

    def __new__(cls) -> "_ThemeManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._current_theme: dict[str, str] = {}
        return cls._instance

    def apply_theme(self, theme_name: str) -> None:
        theme = Colors.THEMES.get(theme_name)
        if theme is None:
            log.warning("Bilinmeyen tema: %s. 'dark' kullaniliyor.", theme_name)
            theme = Colors.THEMES["dark"]

        self._current_theme = theme

        # ComboBox ok ikonu: QSS `url()` dosya yolu ister, QIcon kabul etmez --
        # her tema uygulamasinda `chevron_down.svg`'yi o temanin icon_color'iyla
        # boyayip sabit bir dosyaya yaziyoruz, QSS de o dosyayi referans veriyor.
        _write_themed_svg("chevron_down.svg", theme["icon_color"], _COMBO_ARROW_PATH)
        qss = self._build_qss({**theme, "combo_arrow_path": _COMBO_ARROW_PATH.as_posix()})
        QApplication.instance().setStyleSheet(qss)  # type: ignore[union-attr]

        # Event Bus burada import ediliyor — dairesel import'tan kacmak icin.
        from core.events import event_bus
        event_bus.theme_changed.emit(theme)
        log.info("Tema uygulandi: %s", theme["name"])

    @property
    def current_theme(self) -> dict[str, str]:
        return self._current_theme

    def _build_qss(self, theme: dict[str, str]) -> str:
        qss_parts: list[str] = []
        for qss_file in sorted(_STYLES_DIR.glob("*.qss")):
            try:
                raw = qss_file.read_text(encoding="utf-8")
                for key, value in theme.items():
                    raw = raw.replace("{{" + key + "}}", value)
                qss_parts.append(raw)
            except OSError as exc:
                log.error("QSS dosyasi okunamadi: %s — %s", qss_file, exc)
        return "\n".join(qss_parts)


theme_manager = _ThemeManager()
