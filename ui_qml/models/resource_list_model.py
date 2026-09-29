from typing import Any, Callable

from PySide6.QtCore import Property, QAbstractListModel, QModelIndex, Qt, Signal

from models import Resource, status_label
from utils.date_utils import DATE_FORMAT, format_local_datetime
from utils.url_utils import format_display_url

DEFAULT_CATEGORY_COLOR = "#64748B"


def _meta(resource: Resource) -> dict:
    return resource.extra_metadata or {}


def _thumbnail_url(resource: Resource) -> str:
    meta = _meta(resource)
    return str(meta.get("image") or meta.get("og:image") or meta.get("thumbnail") or "")


def _duration_label(resource: Resource) -> str:
    """Video suresi ("1:02:03" / "4:05"); yoksa ya da sayi degilse bos."""
    try:
        total_seconds = int(_meta(resource).get("duration_seconds") or 0)
    except (TypeError, ValueError):
        return ""
    if not total_seconds:
        return ""
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def _category_color(resource: Resource) -> str:
    category = resource.category
    return category.color_hex if category and category.color_hex else DEFAULT_CATEGORY_COLOR


def _status_value(resource: Resource) -> str:
    return resource.status.value if hasattr(resource.status, "value") else str(resource.status)


class ResourceListModel(QAbstractListModel):
    """QML GridView ve ListView için optimize edilmiş sanallaştırılmış liste modeli."""

    IdRole = Qt.ItemDataRole.UserRole + 1
    TitleRole = Qt.ItemDataRole.UserRole + 2
    UrlRole = Qt.ItemDataRole.UserRole + 3
    DomainRole = Qt.ItemDataRole.UserRole + 4
    CategoryIdRole = Qt.ItemDataRole.UserRole + 5
    CategoryNameRole = Qt.ItemDataRole.UserRole + 6
    CategoryColorRole = Qt.ItemDataRole.UserRole + 7
    StatusRole = Qt.ItemDataRole.UserRole + 8
    StatusLabelRole = Qt.ItemDataRole.UserRole + 9
    PriorityRole = Qt.ItemDataRole.UserRole + 10
    IsPinnedRole = Qt.ItemDataRole.UserRole + 11
    IsFavoriteRole = Qt.ItemDataRole.UserRole + 12
    ContentRole = Qt.ItemDataRole.UserRole + 13
    ThumbnailUrlRole = Qt.ItemDataRole.UserRole + 15
    DescriptionRole = Qt.ItemDataRole.UserRole + 16
    ReadingMinutesRole = Qt.ItemDataRole.UserRole + 17
    TagsRole = Qt.ItemDataRole.UserRole + 18
    CreatedAtRole = Qt.ItemDataRole.UserRole + 19
    DurationLabelRole = Qt.ItemDataRole.UserRole + 20

    # QML `rowCount()` cagrisi degisimi bildirmez (binding bir kez hesaplanip donar);
    # bildirimli `count` property'si QML'in bos-durum/grid gorunurlugunu gunceller.
    countChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._resources: list[Resource] = []

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._resources)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._resources)

    # Rol -> (QML'deki ad, kaynaktan deger ureten fonksiyon). Yeni kart alani eklemek tek satir:
    # rol sabitini tanimlayip buraya bir girdi eklemek yeterli (data()/roleNames() degismez).
    _ROLES: dict[int, tuple[bytes, Callable[[Resource], Any]]] = {
        IdRole: (b"id", lambda r: r.id),
        TitleRole: (b"title", lambda r: r.title or "İsimsiz Kaynak"),
        UrlRole: (b"url", lambda r: r.url or ""),
        DomainRole: (b"domain", lambda r: format_display_url(r.url) if r.url else ""),
        CategoryIdRole: (b"categoryId", lambda r: r.category_id or 0),
        CategoryNameRole: (b"categoryName", lambda r: r.category.name if r.category else ""),
        CategoryColorRole: (b"categoryColor", _category_color),
        StatusRole: (b"status", _status_value),
        StatusLabelRole: (b"statusLabel", lambda r: status_label(r.status)),
        PriorityRole: (b"priority", lambda r: r.priority),
        IsPinnedRole: (b"isPinned", lambda r: bool(r.is_pinned)),
        IsFavoriteRole: (b"isFavorite", lambda r: bool(r.is_favorite)),
        ContentRole: (b"content", lambda r: r.content or ""),
        ThumbnailUrlRole: (b"thumbnailUrl", _thumbnail_url),
        DescriptionRole: (b"description", lambda r: _meta(r).get("description") or ""),
        ReadingMinutesRole: (b"readingMinutes", lambda r: r.reading_minutes or 0),
        TagsRole: (b"tags", lambda r: [{"id": t.id, "name": t.name} for t in r.tags]),
        CreatedAtRole: (b"createdAt", lambda r: format_local_datetime(r.created_at, DATE_FORMAT)),
        DurationLabelRole: (b"durationLabel", _duration_label),
    }

    def roleNames(self) -> dict[int, bytes]:
        return {role: name for role, (name, _getter) in self._ROLES.items()}

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not (0 <= index.row() < len(self._resources)):
            return None
        spec = self._ROLES.get(role)
        return spec[1](self._resources[index.row()]) if spec else None

    def set_resources(self, resources: list[Resource]) -> None:
        self.beginResetModel()
        self._resources = list(resources)
        self.endResetModel()
        self.countChanged.emit()

