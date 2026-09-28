from models import Resource, ResourceStatus, Category, Tag
from ui_qml.models.resource_list_model import ResourceListModel


def test_resource_list_model_roles_and_data(qapp):
    model = ResourceListModel()
    assert model.rowCount() == 0

    cat = Category(id=1, name="Teknoloji", color_hex="#6366F1")
    tag = Tag(id=10, name="ai")
    res = Resource(
        id=100,
        title="Yapay Zeka Makalesi",
        url="https://example.com/ai",
        status=ResourceStatus.IN_PROGRESS,
        priority=3,
        is_pinned=True,
        is_favorite=True,
        content="Notlar burada",
        full_text="<p>Makale metni</p>",
        extra_metadata={"description": "Bir AI makalesi", "reading_time": 5},
    )
    res.category = cat
    res.tags = [tag]

    model.set_resources([res])
    assert model.rowCount() == 1

    idx = model.index(0, 0)
    assert model.data(idx, ResourceListModel.IdRole) == 100
    assert model.data(idx, ResourceListModel.TitleRole) == "Yapay Zeka Makalesi"
    assert model.data(idx, ResourceListModel.DomainRole) == "example.com"
    assert model.data(idx, ResourceListModel.CategoryNameRole) == "Teknoloji"
    assert model.data(idx, ResourceListModel.CategoryColorRole) == "#6366F1"
    assert model.data(idx, ResourceListModel.StatusRole) == "IN_PROGRESS"
    assert model.data(idx, ResourceListModel.IsPinnedRole) is True
    assert model.data(idx, ResourceListModel.IsFavoriteRole) is True
    assert model.data(idx, ResourceListModel.ReadingMinutesRole) == 5
    assert len(model.data(idx, ResourceListModel.TagsRole)) == 1

    # Resource lookup helper test
    r = model.get_resource_by_id(100)
    assert r is not None
    assert r.title == "Yapay Zeka Makalesi"

    assert model.get_resource_by_id(999) is None
