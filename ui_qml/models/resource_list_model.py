from datetime import datetime
from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, Qt, Signal

from models import Resource, ResourceStatus, status_label
from utils.date_utils import DATE_FORMAT, format_local_datetime
from utils.url_utils import format_display_url


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

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.IdRole: b"id",
            self.TitleRole: b"title",
            self.UrlRole: b"url",
            self.DomainRole: b"domain",
            self.CategoryIdRole: b"categoryId",
            self.CategoryNameRole: b"categoryName",
            self.CategoryColorRole: b"categoryColor",
            self.StatusRole: b"status",
            self.StatusLabelRole: b"statusLabel",
            self.PriorityRole: b"priority",
            self.IsPinnedRole: b"isPinned",
            self.IsFavoriteRole: b"isFavorite",
            self.ContentRole: b"content",
            self.ThumbnailUrlRole: b"thumbnailUrl",
            self.DescriptionRole: b"description",
            self.ReadingMinutesRole: b"readingMinutes",
            self.TagsRole: b"tags",
            self.CreatedAtRole: b"createdAt",
            self.DurationLabelRole: b"durationLabel",
        }

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not (0 <= index.row() < len(self._resources)):
            return None

        resource = self._resources[index.row()]
        meta = resource.extra_metadata or {}

        if role == self.IdRole:
            return resource.id
        elif role == self.TitleRole:
            return resource.title or "İsimsiz Kaynak"
        elif role == self.UrlRole:
            return resource.url or ""
        elif role == self.DomainRole:
            return format_display_url(resource.url) if resource.url else ""
        elif role == self.CategoryIdRole:
            return resource.category_id or 0
        elif role == self.CategoryNameRole:
            return resource.category.name if resource.category else ""
        elif role == self.CategoryColorRole:
            return resource.category.color_hex if resource.category and resource.category.color_hex else "#64748B"
        elif role == self.StatusRole:
            return resource.status.value if hasattr(resource.status, "value") else str(resource.status)
        elif role == self.StatusLabelRole:
            return status_label(resource.status)
        elif role == self.PriorityRole:
            return resource.priority
        elif role == self.IsPinnedRole:
            return bool(resource.is_pinned)
        elif role == self.IsFavoriteRole:
            return bool(resource.is_favorite)
        elif role == self.ContentRole:
            return resource.content or ""
        elif role == self.ThumbnailUrlRole:
            thumb = meta.get("image") or meta.get("og:image") or meta.get("thumbnail") or ""
            return str(thumb) if thumb else ""
        elif role == self.DescriptionRole:
            return meta.get("description") or ""
        elif role == self.ReadingMinutesRole:
            return resource.reading_minutes or 0
        elif role == self.TagsRole:
            return [{"id": t.id, "name": t.name} for t in resource.tags]
        elif role == self.CreatedAtRole:
            if resource.created_at:
                return format_local_datetime(resource.created_at, DATE_FORMAT)
            return ""
        elif role == self.DurationLabelRole:
            duration = meta.get("duration_seconds")
            if not duration:
                return ""
            try:
                total_seconds = int(duration)
            except (TypeError, ValueError):
                return ""
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            return f"{minutes}:{seconds:02d}"

        return None

    def set_resources(self, resources: list[Resource]) -> None:
        self.beginResetModel()
        self._resources = list(resources)
        self.endResetModel()
        self.countChanged.emit()

