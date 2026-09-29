import re
from datetime import datetime

import pytest
from PySide6.QtCore import QModelIndex, Qt

from models import Category, Resource, ResourceStatus, Tag
from tests.test_qml.qml_harness import QML_DIR, strip_qml_comments
from ui_qml.models.resource_list_model import ResourceListModel


def _model_with(resource: Resource) -> tuple[ResourceListModel, QModelIndex]:
    model = ResourceListModel()
    model.set_resources([resource])
    return model, model.index(0, 0)


def _resource(**overrides) -> Resource:
    defaults = dict(id=1, title="Baslik", status=ResourceStatus.PLANNED, priority=2)
    defaults.update(overrides)
    return Resource(**defaults)


def _by_name(model: ResourceListModel, index: QModelIndex) -> dict:
    return {bytes(name).decode(): model.data(index, role) for role, name in model.roleNames().items()}


def test_every_role_has_a_unique_qml_name_and_a_getter(qapp):
    model = ResourceListModel()
    names = [bytes(n).decode() for n in model.roleNames().values()]

    assert len(names) == len(set(names)) == 19
    assert set(model.roleNames()) == set(ResourceListModel._ROLES)


def test_all_roles_for_a_fully_populated_resource(qapp):
    resource = _resource(
        title="Yapay Zeka", url="https://www.youtube.com/watch?v=1", category_id=3, priority=3, is_pinned=True,
        is_favorite=True, content="not", reading_minutes=7, created_at=datetime(2026, 9, 29, 22, 30),
        status=ResourceStatus.IN_PROGRESS,
        extra_metadata={"description": "aciklama", "og:image": "https://x/i.png", "duration_seconds": 3723},
    )
    resource.category = Category(id=3, name="Video", color_hex="#FF0000")
    resource.tags = [Tag(id=9, name="ai")]
    model, index = _model_with(resource)

    data = _by_name(model, index)

    assert data["id"] == 1 and data["title"] == "Yapay Zeka" and data["priority"] == 3
    assert data["domain"] == "youtube" and data["url"].startswith("https://www.youtube.com")
    assert (data["categoryId"], data["categoryName"], data["categoryColor"]) == (3, "Video", "#FF0000")
    assert data["status"] == "IN_PROGRESS" and data["statusLabel"]
    assert data["isPinned"] is True and data["isFavorite"] is True and data["content"] == "not"
    assert data["thumbnailUrl"] == "https://x/i.png" and data["description"] == "aciklama"
    assert data["readingMinutes"] == 7 and data["tags"] == [{"id": 9, "name": "ai"}]
    assert data["durationLabel"] == "1:02:03"
    assert re.fullmatch(r"\d\d\.\d\d\.\d{4}", data["createdAt"])


def test_defaults_for_a_minimal_resource(qapp):
    model, index = _model_with(_resource(title=None))

    data = _by_name(model, index)

    assert data["title"] == "İsimsiz Kaynak"
    assert (data["url"], data["domain"], data["content"], data["description"], data["thumbnailUrl"]) == ("",) * 5
    assert (data["categoryId"], data["categoryName"], data["categoryColor"]) == (0, "", "#64748B")
    assert data["readingMinutes"] == 0 and data["durationLabel"] == "" and data["createdAt"] == ""
    assert data["isPinned"] is False and data["isFavorite"] is False and data["tags"] == []


@pytest.mark.parametrize(
    ("meta", "expected"),
    [
        ({"duration_seconds": 245}, "4:05"),
        ({"duration_seconds": 59}, "0:59"),
        ({"duration_seconds": 3600}, "1:00:00"),
        ({"duration_seconds": "125"}, "2:05"),
        ({"duration_seconds": 0}, ""),
        ({"duration_seconds": "abc"}, ""),
        ({"duration_seconds": None}, ""),
        ({}, ""),
    ],
)
def test_duration_label(qapp, meta, expected):
    model, index = _model_with(_resource(extra_metadata=meta or None))

    assert model.data(index, ResourceListModel.DurationLabelRole) == expected


@pytest.mark.parametrize(
    ("meta", "expected"),
    [
        ({"image": "a", "og:image": "b", "thumbnail": "c"}, "a"),
        ({"og:image": "b", "thumbnail": "c"}, "b"),
        ({"thumbnail": "c"}, "c"),
        ({}, ""),
    ],
)
def test_thumbnail_source_priority(qapp, meta, expected):
    model, index = _model_with(_resource(extra_metadata=meta))

    assert model.data(index, ResourceListModel.ThumbnailUrlRole) == expected


def test_unknown_role_and_invalid_index_return_none(qapp):
    model, index = _model_with(_resource())

    assert model.data(index, Qt.ItemDataRole.UserRole + 999) is None
    assert model.data(model.index(5, 0), ResourceListModel.IdRole) is None
    assert model.data(QModelIndex(), ResourceListModel.IdRole) is None


def test_qml_only_reads_roles_the_model_provides(qapp):
    """Kartlar `model.<ad>` ile rol okur; olmayan bir role basvurulursa sessizce undefined olur."""
    provided = {bytes(n).decode() for n in ResourceListModel().roleNames().values()}
    used = set()
    for name in ("AppCard.qml",):
        source = strip_qml_comments((QML_DIR / "components" / name).read_text(encoding="utf-8"))
        used |= set(re.findall(r"\bmodel\.(\w+)", source))

    assert used, "AppCard model rollerini kullanmali"
    assert used <= provided, f"modelde olmayan roller: {used - provided}"
