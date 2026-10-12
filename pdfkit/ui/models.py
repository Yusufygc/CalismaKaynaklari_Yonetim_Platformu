from bisect import bisect_left
from dataclasses import dataclass

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
    Signal,
)

from pdfkit.domain.annotations import Annotation
from pdfkit.domain.labels import effective_color, name_for_label

_NO_PAGE = 1 << 30


@dataclass
class _Row:
    """Bir alinti + QML icin onceden hesaplanmis turevleri (her `data()` cagrisinda tekrar hesaplanmasin)."""

    annotation: Annotation
    polygons: list
    bounding_rect: list
    pages: list
    sort_key: tuple

    @classmethod
    def of(cls, annotation: Annotation) -> "_Row":
        polygons = [
            [[x, y] for x, y in polygon]
            for segment in annotation.segments
            for polygon in (segment.polygons or [])
        ]
        points = [point for polygon in polygons for point in polygon]
        if points:
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            rect = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
        else:
            rect = []
        first = annotation.segments[0] if annotation.segments else None
        key = (first.page if first else _NO_PAGE, first.start if first else 0, annotation.id)
        return cls(annotation, polygons, rect, sorted({s.page for s in annotation.segments}), key)


class AnnotationListModel(QAbstractListModel):
    """Acik belgenin alintilari. Yapisal degisiklikler (ekle/sil) yalnizca etkilenen satir icin sinyal yayar;
    boylece QML'deki tum sayfa katmanlari yeniden kurulmaz."""

    countChanged = Signal()

    IdRole = Qt.UserRole + 1
    UidRole = Qt.UserRole + 2
    PageRole = Qt.UserRole + 3
    PagesRole = Qt.UserRole + 4
    LabelKeyRole = Qt.UserRole + 5
    LabelRole = Qt.UserRole + 6
    ColorRole = Qt.UserRole + 7
    CommentRole = Qt.UserRole + 8
    TagsRole = Qt.UserRole + 9
    QuoteRole = Qt.UserRole + 10
    StatusRole = Qt.UserRole + 11
    PolygonsRole = Qt.UserRole + 12
    BoundingRectRole = Qt.UserRole + 13
    HasGeometryRole = Qt.UserRole + 14

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[_Row] = []
        self._keys: list[tuple] = []  # _rows ile paralel siralama anahtarlari (bisect icin)
        self._by_id: dict[int, _Row] = {}

    # ---- Qt arayuzu ----
    def roleNames(self) -> dict:
        return {
            self.IdRole: b"annotationId",
            self.UidRole: b"uid",
            self.PageRole: b"page",
            self.PagesRole: b"pages",
            self.LabelKeyRole: b"labelKey",
            self.LabelRole: b"label",
            self.ColorRole: b"color",
            self.CommentRole: b"comment",
            self.TagsRole: b"tags",
            self.QuoteRole: b"quote",
            self.StatusRole: b"status",
            self.PolygonsRole: b"polygons",
            self.BoundingRectRole: b"boundingRect",
            self.HasGeometryRole: b"hasGeometry",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row = self._rows[index.row()]
        annotation = row.annotation
        values = {
            self.IdRole: annotation.id,
            self.UidRole: annotation.uid,
            self.PageRole: annotation.page if annotation.page is not None else -1,
            self.PagesRole: row.pages,
            self.LabelKeyRole: annotation.label_key,
            self.LabelRole: name_for_label(annotation.label_key),
            self.ColorRole: effective_color(annotation.label_key, annotation.color),
            self.CommentRole: annotation.comment or "",
            self.TagsRole: annotation.tags,
            self.QuoteRole: annotation.quote_exact,
            self.StatusRole: annotation.status,
            self.PolygonsRole: row.polygons,
            self.BoundingRectRole: row.bounding_rect,
            self.HasGeometryRole: bool(row.polygons),
        }
        return values.get(role)

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)

    # ---- icerik ----
    def set_annotations(self, annotations: list[Annotation]) -> None:
        self.beginResetModel()
        self._rows = sorted((_Row.of(a) for a in annotations), key=lambda r: r.sort_key)
        self._keys = [r.sort_key for r in self._rows]
        self._by_id = {r.annotation.id: r for r in self._rows}
        self.endResetModel()
        self.countChanged.emit()

    def clear(self) -> None:
        if self._rows:
            self.set_annotations([])

    def upsert(self, annotation: Annotation) -> None:
        """Yeni alintiyi sirali yerine ekler; var olani yerinde gunceller (sayfa/konum degistiyse tasir)."""
        new_row = _Row.of(annotation)
        current = self._by_id.get(annotation.id)
        if current is not None:
            position = bisect_left(self._keys, current.sort_key)
            if current.sort_key == new_row.sort_key:
                self._rows[position] = new_row
                self._by_id[annotation.id] = new_row
                self.dataChanged.emit(self.index(position), self.index(position))
                return
            self.remove(annotation.id)
        position = bisect_left(self._keys, new_row.sort_key)
        self.beginInsertRows(QModelIndex(), position, position)
        self._rows.insert(position, new_row)
        self._keys.insert(position, new_row.sort_key)
        self._by_id[annotation.id] = new_row
        self.endInsertRows()
        self.countChanged.emit()

    def remove(self, annotation_id: int) -> bool:
        row = self._by_id.get(annotation_id)
        if row is None:
            return False
        position = bisect_left(self._keys, row.sort_key)
        self.beginRemoveRows(QModelIndex(), position, position)
        del self._rows[position]
        del self._keys[position]
        del self._by_id[annotation_id]
        self.endRemoveRows()
        self.countChanged.emit()
        return True

    # ---- Python tarafi sorgular ----
    def annotation(self, annotation_id: int) -> Annotation | None:
        row = self._by_id.get(annotation_id)
        return row.annotation if row else None

    def annotations_on_page(self, page: int) -> list[Annotation]:
        return [r.annotation for r in self._rows if page in r.pages]

    def row_pages(self, source_row: int) -> list[int]:
        return self._rows[source_row].pages

    def row_label_key(self, source_row: int) -> str:
        return self._rows[source_row].annotation.label_key


class PageFilterModel(QSortFilterProxyModel):
    """Tek bir sayfanin (ve istege bagli tek anlam etiketinin) alintilari. Sayfa delegesi basina bir tane."""

    pageChanged = Signal()
    labelKeyChanged = Signal()

    def __init__(self, source: AnnotationListModel, page: int = -1, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._page = page
        self._label_key = ""
        self.setSourceModel(source)

    @Property(int, notify=pageChanged)
    def page(self) -> int:
        return self._page

    @page.setter
    def page(self, value: int) -> None:
        if value != self._page:
            self.beginFilterChange()
            self._page = value
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
            self.pageChanged.emit()

    @Property(str, notify=labelKeyChanged)
    def labelKey(self) -> str:
        return self._label_key

    @labelKey.setter
    def labelKey(self, value: str) -> None:
        if value != self._label_key:
            self.beginFilterChange()
            self._label_key = value
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
            self.labelKeyChanged.emit()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        source = self.sourceModel()
        if self._page >= 0 and self._page not in source.row_pages(source_row):
            return False
        return not self._label_key or source.row_label_key(source_row) == self._label_key
