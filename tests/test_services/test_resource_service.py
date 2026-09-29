import pytest

from core.exceptions import InvalidURLError, ValidationError
from models import Resource, ResourceStatus
from services.category_service import CategoryService
from services.resource_service import ResourceService
from services.schemas import ResourceCreateSchema, ResourceUpdateSchema


def test_deleting_category_keeps_resource_and_clears_category(session):
    category = CategoryService(session).create_category("Python", "#3776AB")
    resource = ResourceService(session).add_new_resource(
        ResourceCreateSchema(
            title="Docs",
            category_id=category.id,
            extra_metadata={},
        )
    )

    CategoryService(session).delete_category(category.id)
    session.expire_all()

    persisted = session.get(Resource, resource.id)
    assert persisted is not None
    assert persisted.category_id is None


def test_add_resource_auto_assigns_category_from_url(session):
    resource = ResourceService(session).add_new_resource(
        ResourceCreateSchema(title="Video", url="https://youtu.be/abc123")
    )

    assert resource.category is not None
    assert resource.category.name == "YouTube"
    assert resource.category.color_hex == "#EF4444"


def test_add_resource_respects_explicit_category_over_auto_detect(session):
    category = CategoryService(session).create_category("Ozel", "#000000")
    resource = ResourceService(session).add_new_resource(
        ResourceCreateSchema(
            title="Video", url="https://youtu.be/abc123", category_id=category.id
        )
    )

    assert resource.category_id == category.id


def test_add_resource_deduplicates_tag_names(session):
    resource = ResourceService(session).add_new_resource(
        ResourceCreateSchema(
            title="Tags",
            tag_names=["Python", " python ", "SQL"],
        )
    )

    assert [tag.name for tag in resource.tags] == ["python", "sql"]


def test_update_resource_replaces_tag_names(session):
    service = ResourceService(session)
    resource = service.add_new_resource(
        ResourceCreateSchema(title="Tags", tag_names=["old"])
    )

    updated = service.update_resource(
        resource.id, ResourceUpdateSchema(tag_names=["new", "NEW"])
    )

    assert [tag.name for tag in updated.tags] == ["new"]


def test_update_resource_with_empty_tag_list_clears_tags(session):
    service = ResourceService(session)
    resource = service.add_new_resource(
        ResourceCreateSchema(title="Tags", tag_names=["old"])
    )

    updated = service.update_resource(resource.id, ResourceUpdateSchema(tag_names=[]))

    assert updated.tags == []


def test_add_resource_accepts_local_file_url(session, tmp_path):
    pdf_path = tmp_path / "yerel.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    resource = ResourceService(session).add_new_resource(
        ResourceCreateSchema(title="Yerel PDF", url=pdf_path.as_uri())
    )

    assert resource.url == pdf_path.as_uri()


def test_add_resource_merges_url_tag_with_manual_tags(session):
    resource = ResourceService(session).add_new_resource(
        ResourceCreateSchema(
            title="Video",
            url="https://youtu.be/abc123",
            tag_names=["AI", "youtube"],
        )
    )

    assert [tag.name for tag in resource.tags] == ["ai", "youtube"]


@pytest.mark.parametrize(
    ("url", "expected_tag"),
    [
        ("https://www.linkedin.com/posts/example", "linkedin"),
        ("https://instagram.com/reel/abc", "instagram"),
        ("https://github.com/example/repo", "github"),
        ("https://docs.python.org/3/", "python"),
    ],
)
def test_add_resource_derives_tags_from_url(session, url, expected_tag):
    resource = ResourceService(session).add_new_resource(
        ResourceCreateSchema(title="URL", url=url)
    )

    assert [tag.name for tag in resource.tags] == [expected_tag]


def test_update_url_adds_new_url_tag_and_preserves_existing_tags(session):
    service = ResourceService(session)
    resource = service.add_new_resource(
        ResourceCreateSchema(
            title="URL",
            url="https://github.com/example/repo",
            tag_names=["manual"],
        )
    )

    updated = service.update_resource(
        resource.id,
        ResourceUpdateSchema(url="https://www.linkedin.com/posts/example"),
    )

    assert [tag.name for tag in updated.tags] == ["manual", "github", "linkedin"]


@pytest.mark.parametrize(
    "status",
    [
        ResourceStatus.INBOX,
        ResourceStatus.PLANNED,
        ResourceStatus.IN_PROGRESS,
        ResourceStatus.COMPLETED,
    ],
)
def test_status_update_is_manual(session, status):
    service = ResourceService(session)
    resource = service.add_new_resource(ResourceCreateSchema(title="Status"))

    updated = service.update_resource(resource.id, ResourceUpdateSchema(status=status))

    assert updated.status == status


@pytest.mark.parametrize(
    ("data", "expected_error"),
    [
        ({"title": "Bad URL", "url": "ftp://example.com"}, InvalidURLError),
        ({"title": "Bad Priority", "priority": 9}, ValidationError),
    ],
)
def test_validation_errors_leave_session_usable(session, data, expected_error):
    service = ResourceService(session)

    with pytest.raises(expected_error):
        service.add_new_resource(ResourceCreateSchema(**data))

    resource = service.add_new_resource(ResourceCreateSchema(title="Valid"))
    assert resource.id is not None


def test_toggle_pin_flips_value(session):
    service = ResourceService(session)
    resource = service.add_new_resource(ResourceCreateSchema(title="Pin Me"))
    assert resource.is_pinned is False

    service.toggle_pin(resource.id)
    session.expire_all()
    assert session.get(Resource, resource.id).is_pinned is True

    service.toggle_pin(resource.id)
    session.expire_all()
    assert session.get(Resource, resource.id).is_pinned is False


def test_toggle_favorite_flips_value(session):
    service = ResourceService(session)
    resource = service.add_new_resource(ResourceCreateSchema(title="Star Me"))
    assert resource.is_favorite is False

    service.toggle_favorite(resource.id)
    session.expire_all()
    assert session.get(Resource, resource.id).is_favorite is True


def test_query_resources_combines_filters(session):
    service = ResourceService(session)
    r1 = service.add_new_resource(
        ResourceCreateSchema(title="Hi", status=ResourceStatus.INBOX, priority=1)
    )
    service.add_new_resource(
        ResourceCreateSchema(title="Lo", status=ResourceStatus.PLANNED, priority=3)
    )
    service.toggle_favorite(r1.id)

    results = service.query_resources(
        {"statuses": [ResourceStatus.INBOX], "priorities": [1]}
    )
    assert [r.id for r in results] == [r1.id]

    favs = service.query_resources({"favorites_only": True})
    assert [r.id for r in favs] == [r1.id]


def test_query_resources_orders_pinned_first(session):
    service = ResourceService(session)
    old = service.add_new_resource(ResourceCreateSchema(title="Old"))
    new = service.add_new_resource(ResourceCreateSchema(title="New"))

    service.toggle_pin(old.id)

    results = service.query_resources({})
    assert results[0].id == old.id  # pinned > created_at
    assert results[1].id == new.id


def test_query_resources_supports_scalar_and_alias_filter_keys(session):
    service = ResourceService(session)
    r1 = service.add_new_resource(
        ResourceCreateSchema(title="Inbox Resource", status=ResourceStatus.INBOX, priority=1)
    )
    r2 = service.add_new_resource(
        ResourceCreateSchema(title="Done Resource", status=ResourceStatus.COMPLETED, priority=2)
    )
    service.toggle_favorite(r1.id)

    # Test single status alias
    res_status = service.query_resources({"status": ResourceStatus.INBOX})
    assert [r.id for r in res_status] == [r1.id]

    # Test is_favorite alias
    res_fav = service.query_resources({"is_favorite": True})
    assert [r.id for r in res_fav] == [r1.id]

    # Test single priority alias
    res_pri = service.query_resources({"priority": 2})
    assert [r.id for r in res_pri] == [r2.id]

