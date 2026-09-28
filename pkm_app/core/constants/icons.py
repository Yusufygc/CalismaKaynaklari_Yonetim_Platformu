from core.paths import resource_path

ICONS_DIR = resource_path("assets", "icons")


class QtAwesomeIcons:
    """qtawesome ikon isimleri."""
    INBOX = "fa5s.inbox"
    PLANNED = "fa5s.clock"
    FAVORITES = "fa5s.star"
    URL_SHOWCASE = "fa5s.globe"
    SETTINGS = "fa5s.cog"

    # Arama & Input
    OPEN_BROWSER = "fa5s.external-link-alt"
    CLOSE = "fa5s.times"
    CATEGORY = "fa5s.folder"
    ADD = "fa5s.plus-circle"
    PINNED = "fa5s.thumbtack"
    FAVORITE = "fa5s.star"
    FAVORITE_OUTLINE = "fa5s.star"  # qtawesome free FA5 regular yok; solid kullan, renk farki ile
    DELETE = "fa5s.trash-alt"
    EDIT = "fa5s.pen"
    FILTER_CLEAR = "fa5s.times-circle"
    KNOWLEDGE_POOL = "fa5s.book"
    READ = "fa5s.book-open"
    BACK = "fa5s.arrow-left"
