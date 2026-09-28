from core.themes.dark import DARK_THEME
from core.themes.light import LIGHT_THEME


class Colors:
    """
    Aktif tema sozlugune erisim icin yardimci sinif.
    Dogrudan HEX kullanmak yerine ThemeManager uzerinden renk alinmalidir;
    bu sinif sadece tema anahtarlarini sabit olarak tutar.
    """

    # Tema anahtar sabitleri
    BG_PRIMARY = "bg_primary"
    BG_SECONDARY = "bg_secondary"
    TEXT_PRIMARY = "text_primary"
    TEXT_SECONDARY = "text_secondary"
    ACCENT = "accent_color"
    BORDER = "border_color"
    ICON = "icon_color"
    ON_ACCENT = "on_accent"
    DANGER = "danger_color"
    DANGER_BG = "danger_bg"
    DANGER_HOVER = "danger_hover"
    STATUS_PLANNED = "status_planned"
    STATUS_IN_PROGRESS = "status_in_progress"
    STATUS_COMPLETED = "status_completed"
    TAG_BADGE_BG = "tag_badge_bg"
    THUMBNAIL_BG = "thumbnail_bg"
    CATEGORY_FALLBACK = "category_fallback"
    SWATCH_BORDER = "swatch_border"
    ACCENT_SECONDARY = "accent_secondary"
    ACCENT_GRADIENT_START = "accent_gradient_start"
    ACCENT_GRADIENT_END = "accent_gradient_end"
    SURFACE_HOVER = "surface_hover"
    SURFACE_ELEVATED = "surface_elevated"
    FOCUS_RING = "focus_ring"
    SHADOW = "shadow_color"
    MUTED_BADGE_BG = "muted_badge_bg"
    SUCCESS = "success_color"
    WARNING = "warning_color"
    BUTTON_PRESSED = "button_pressed"
    NAV_SELECTED_BG = "nav_selected_bg"
    HIGHLIGHT_COLOR = "highlight_color"

    THEMES = {
        "dark": DARK_THEME,
        "light": LIGHT_THEME,
    }
