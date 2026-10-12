import pytest
from PySide6.QtCore import QModelIndex

from pdfkit.domain.annotations import STATUS_OK, Annotation, Segment
from pdfkit.ui.models import AnnotationListModel, PageFilterModel

SQUARE = [(10.0, 20.0), (50.0, 20.0), (50.0, 30.0), (10.0, 30.0)]


def _annotation(annotation_id, page=0, start=0, label="finding", color=None, polygons=True, comment=None):
    return Annotation(
        id=annotation_id, uid=f"U{annotation_id:025d}", document_id=1, label_key=label, color=color, comment=comment,
        tags=["a"], quote_exact=f"alinti {annotation_id}", quote_prefix=None, quote_suffix=None,
        segments=[Segment(page, start, start + 5, "metin", [SQUARE] if polygons else None)],
        engine_fp="fp", status=STATUS_OK,
    )


def _roles(model):
    return {bytes(name).decode(): role for role, name in model.roleNames().items()}


def _value(model, row, name):
    return model.data(model.index(row), _roles(model)[name])


@pytest.fixture()
def model(qapp):
    return AnnotationListModel()


class Recorder:
    def __init__(self, model):
        self.events = []
        model.rowsInserted.connect(lambda p, a, b: self.events.append(("inserted", a, b)))
        model.rowsRemoved.connect(lambda p, a, b: self.events.append(("removed", a, b)))
        model.dataChanged.connect(lambda a, b, r=None: self.events.append(("changed", a.row(), b.row())))
        model.modelReset.connect(lambda: self.events.append(("reset",)))


def test_items_are_sorted_by_page_then_position_and_expose_qml_roles(model):
    model.set_annotations([_annotation(1, page=2), _annotation(2, page=0, start=40), _annotation(3, page=0, start=5)])

    assert [_value(model, r, "annotationId") for r in range(3)] == [3, 2, 1]
    assert model.rowCount() == 3 and model.count == 3
    assert _value(model, 0, "color") == "#22C55E" and _value(model, 0, "label") == "Bulgu / Sonuç"
    assert _value(model, 0, "polygons") == [[[10.0, 20.0], [50.0, 20.0], [50.0, 30.0], [10.0, 30.0]]]
    assert _value(model, 0, "boundingRect") == [10.0, 20.0, 40.0, 10.0]
    assert _value(model, 0, "hasGeometry") is True and _value(model, 0, "pages") == [0]


def test_effective_color_prefers_explicit_color_then_label_then_default(model):
    model.set_annotations([_annotation(1, color="#123456"), _annotation(2, start=10, label="general")])

    assert _value(model, 0, "color") == "#123456"
    assert _value(model, 1, "color") == "#B45309"


def test_annotation_without_geometry_has_empty_rect(model):
    model.set_annotations([_annotation(1, polygons=False)])

    assert _value(model, 0, "polygons") == [] and _value(model, 0, "boundingRect") == []
    assert _value(model, 0, "hasGeometry") is False


def test_insert_remove_and_update_emit_only_row_level_signals(model):
    model.set_annotations([_annotation(1, start=0), _annotation(3, start=20)])
    recorder = Recorder(model)

    model.upsert(_annotation(2, start=10))  # ortaya eklenir
    model.upsert(_annotation(2, start=10, comment="yorum"))  # yerinde guncellenir
    assert model.remove(1)
    assert not model.remove(999)

    assert recorder.events == [("inserted", 1, 1), ("changed", 1, 1), ("removed", 0, 0)]
    assert [_value(model, r, "annotationId") for r in range(2)] == [2, 3]
    assert _value(model, 0, "comment") == "yorum"


def test_moved_annotation_is_removed_and_reinserted_at_its_new_place(model):
    model.set_annotations([_annotation(1, page=0), _annotation(2, page=1)])
    recorder = Recorder(model)

    model.upsert(_annotation(1, page=3))  # yeniden baglama sonrasi baska sayfaya tasindi

    assert recorder.events == [("removed", 0, 0), ("inserted", 1, 1)]
    assert [_value(model, r, "annotationId") for r in range(2)] == [2, 1]


def test_count_signal_follows_content(model):
    changes = []
    model.countChanged.connect(lambda: changes.append(model.count))

    model.set_annotations([_annotation(1)])
    model.upsert(_annotation(2, start=9))
    model.remove(1)
    model.clear()

    assert changes == [1, 2, 1, 0]


def test_invalid_index_returns_none(model):
    model.set_annotations([_annotation(1)])

    assert model.data(QModelIndex(), _roles(model)["annotationId"]) is None
    assert model.data(model.index(5), _roles(model)["annotationId"]) is None


def test_page_filter_shows_only_its_page_and_follows_incremental_changes(model):
    model.set_annotations([_annotation(1, page=0), _annotation(2, page=1), _annotation(3, page=1, start=9)])
    page_one = PageFilterModel(model, 1)
    page_zero = PageFilterModel(model, 0)

    assert page_one.rowCount() == 2 and page_zero.rowCount() == 1

    model.upsert(_annotation(4, page=1, start=20))
    model.remove(2)
    assert [page_one.data(page_one.index(r, 0), _roles(model)["annotationId"]) for r in range(page_one.rowCount())] == [3, 4]
    assert page_zero.rowCount() == 1  # baska sayfanin degisikligi bu gorunumu etkilemez


def test_page_filter_label_filter_and_property_changes(model):
    model.set_annotations([_annotation(1, label="method"), _annotation(2, label="finding", start=9)])
    view = PageFilterModel(model, 0)
    changes = []
    view.labelKeyChanged.connect(lambda: changes.append("label"))

    view.labelKey = "method"
    view.labelKey = "method"  # ayni deger: sinyal yok
    assert view.rowCount() == 1 and changes == ["label"]

    view.labelKey = ""
    view.page = 5
    assert view.rowCount() == 0


def test_multi_page_annotation_is_visible_on_each_of_its_pages(model):
    spanning = _annotation(1, page=0)
    spanning.segments.append(Segment(1, 0, 8, "devam", [SQUARE]))
    model.set_annotations([spanning])

    assert PageFilterModel(model, 0).rowCount() == 1 and PageFilterModel(model, 1).rowCount() == 1
    assert PageFilterModel(model, 2).rowCount() == 0
