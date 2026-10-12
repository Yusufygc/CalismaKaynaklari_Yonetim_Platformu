from bisect import bisect_left
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
    Signal,
)

from pdfkit.domain.annotations import Annotation, PageNote
from pdfkit.domain.labels import effective_color, name_for_label

_NO_PAGE = 1 << 30
BULK_RESET_THRESHOLD = 16  # bu kadardan fazla oge birlikte silinirse tek model sifirlamasi


class _IncrementalModel(QAbstractListModel):
    """Sirali, kimlikle erisilen liste modeli. Yapisal degisiklikler (ekle/sil/tasi) yalnizca etkilenen satir
    icin sinyal yayar; boylece QML'deki sayfa katmanlari her degisimde yeniden kurulmaz.

    Alt siniflar `_build(item)` ile satir uretir; satir `item_id`, `sort_key` (kimligi de iceren, benzersiz) ve
    `pages` tasimalidir."""

    countChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[Any] = []
        self._keys: list[tuple] = []  # _rows ile paralel siralama anahtarlari (bisect icin)
        self._by_id: dict[int, Any] = {}

    def _build(self, item: Any) -> Any:  # pragma: no cover - alt sinif sorumlulugu
        raise NotImplementedError

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)

    def _set_items(self, items: list[Any]) -> None:
        self.beginResetModel()
        self._rows = sorted((self._build(item) for item in items), key=lambda r: r.sort_key)
        self._keys = [r.sort_key for r in self._rows]
        self._by_id = {r.item_id: r for r in self._rows}
        self.endResetModel()
        self.countChanged.emit()

    def clear(self) -> None:
        if self._rows:
            self._set_items([])

    def _upsert(self, item: Any) -> None:
        """Yeni ogeyi sirali yerine ekler; var olani yerinde gunceller (konumu degistiyse tasir)."""
        new_row = self._build(item)
        current = self._by_id.get(new_row.item_id)
        if current is not None:
            position = bisect_left(self._keys, current.sort_key)
            if current.sort_key == new_row.sort_key:
                self._rows[position] = new_row
                self._by_id[new_row.item_id] = new_row
                self.dataChanged.emit(self.index(position), self.index(position))
                return
            self.remove(new_row.item_id)
        position = bisect_left(self._keys, new_row.sort_key)
        self.beginInsertRows(QModelIndex(), position, position)
        self._rows.insert(position, new_row)
        self._keys.insert(position, new_row.sort_key)
        self._by_id[new_row.item_id] = new_row
        self.endInsertRows()
        self.countChanged.emit()

    def remove(self, item_id: int) -> bool:
        row = self._by_id.get(item_id)
        if row is None:
            return False
        position = bisect_left(self._keys, row.sort_key)
        self.beginRemoveRows(QModelIndex(), position, position)
        del self._rows[position]
        del self._keys[position]
        del self._by_id[item_id]
        self.endRemoveRows()
        self.countChanged.emit()
        return True

    def remove_many(self, item_ids: list[int]) -> int:
        """Birden cok ogeyi siler. Az sayida ise tek tek (QML satir animasyonlari/kaydirma korunur); cok ise tek
        model sifirlamasi: her satir silmesi tum sayfa suzgeclerine ve gorunur delegelere ulasir, toplu silmede
        bu toplam maliyet donma esigini asar."""
        doomed = {i for i in item_ids if i in self._by_id}
        if len(doomed) <= BULK_RESET_THRESHOLD:
            return sum(1 for item_id in doomed if self.remove(item_id))
        self.beginResetModel()
        self._rows = [r for r in self._rows if r.item_id not in doomed]
        self._keys = [r.sort_key for r in self._rows]
        self._by_id = {r.item_id: r for r in self._rows}
        self.endResetModel()
        self.countChanged.emit()
        return len(doomed)

    # ---- PageFilterModel icin hizli erisim ----
    def row_pages(self, source_row: int) -> list[int]:
        return self._rows[source_row].pages

    def row_label_key(self, source_row: int) -> str:
        return getattr(self._rows[source_row], "label_key", "")


@dataclass
class _AnnotationRow:
    """Bir alinti + QML icin onceden hesaplanmis turevleri (her `data()` cagrisinda tekrar hesaplanmasin)."""

    annotation: Annotation
    polygons: list
    bounding_rect: list
    pages: list
    sort_key: tuple

    @property
    def item_id(self) -> int:
        return self.annotation.id

    @property
    def label_key(self) -> str:
        return self.annotation.label_key

    @classmethod
    def of(cls, annotation: Annotation) -> "_AnnotationRow":
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


class AnnotationListModel(_IncrementalModel):
    """Acik belgenin alintilari (sayfa ve konuma gore sirali)."""

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

    def _build(self, item: Annotation) -> _AnnotationRow:
        return _AnnotationRow.of(item)

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

    def set_annotations(self, annotations: list[Annotation]) -> None:
        self._set_items(annotations)

    def upsert(self, annotation: Annotation) -> None:
        self._upsert(annotation)

    def annotation(self, annotation_id: int) -> Annotation | None:
        row = self._by_id.get(annotation_id)
        return row.annotation if row else None

    def annotations_on_page(self, page: int) -> list[Annotation]:
        return [r.annotation for r in self._rows if page in r.pages]

    def find_by_uid(self, uid: str) -> tuple[Annotation, list] | None:
        """Kararli kimlikle alinti ve sinirlayici dikdortgeni ([x, y, w, h] ya da []); yoksa None."""
        for row in self._rows:
            if row.annotation.uid == uid:
                return row.annotation, row.bounding_rect
        return None

    def count_with_status(self, status: str) -> int:
        return sum(1 for r in self._rows if r.annotation.status == status)

    def tag_counts(self) -> list[tuple[str, int]]:
        """Belgedeki serbest etiketler ve kullanim sayilari (cok kullanilandan aza, esitte ada gore)."""
        counts: dict[str, int] = {}
        for row in self._rows:
            for tag in row.annotation.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))

    def rows_with_rect(self) -> list[tuple[Annotation, list]]:
        """Tum alintilar ve sinirlayici dikdortgenleri ([x, y, w, h] ya da []), model sirasiyla."""
        return [(r.annotation, r.bounding_rect) for r in self._rows]


@dataclass
class _NoteRow:
    note: PageNote

    @property
    def item_id(self) -> int:
        return self.note.id

    @property
    def sort_key(self) -> tuple:
        return (self.note.page, self.note.id)

    @property
    def pages(self) -> list[int]:
        return [self.note.page]


class NoteListModel(_IncrementalModel):
    """Acik belgenin sayfa notlari (sayfa noktasi uzayinda x, y)."""

    IdRole = Qt.UserRole + 1
    UidRole = Qt.UserRole + 2
    PageRole = Qt.UserRole + 3
    XRole = Qt.UserRole + 4
    YRole = Qt.UserRole + 5
    TextRole = Qt.UserRole + 6

    def _build(self, item: PageNote) -> _NoteRow:
        return _NoteRow(item)

    def roleNames(self) -> dict:
        return {
            self.IdRole: b"noteId",
            self.UidRole: b"uid",
            self.PageRole: b"notePage",
            self.XRole: b"noteX",
            self.YRole: b"noteY",
            self.TextRole: b"noteText",
        }

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        note = self._rows[index.row()].note
        return {
            self.IdRole: note.id,
            self.UidRole: note.uid,
            self.PageRole: note.page,
            self.XRole: note.x,
            self.YRole: note.y,
            self.TextRole: note.text,
        }.get(role)

    def set_notes(self, notes: list[PageNote]) -> None:
        self._set_items(notes)

    def upsert(self, note: PageNote) -> None:
        self._upsert(note)

    def note(self, note_id: int) -> PageNote | None:
        row = self._by_id.get(note_id)
        return row.note if row else None

    def all_notes(self) -> list[PageNote]:
        return [r.note for r in self._rows]


class PageFilterModel(QSortFilterProxyModel):
    """Tek bir sayfanin (ve istege bagli tek anlam etiketinin) ogeleri. Sayfa delegesi basina bir tane."""

    pageChanged = Signal()
    labelKeyChanged = Signal()

    def __init__(self, source: _IncrementalModel, page: int = -1, parent: QObject | None = None) -> None:
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
