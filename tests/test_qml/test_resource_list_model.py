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


def test_count_property_notifies_on_reset(qapp):
    """QML rowCount() cagrisi degisimi bildirmez; count property'si bildirim vermeli
    (bos DB ile acilip sonradan kaynak eklenince kartlarin gorunmemesi hatasi)."""
    model = ResourceListModel()
    notified = []
    model.countChanged.connect(lambda: notified.append(model.count))

    model.set_resources([Resource(title="A"), Resource(title="B")])
    model.set_resources([])

    assert notified == [2, 0]

