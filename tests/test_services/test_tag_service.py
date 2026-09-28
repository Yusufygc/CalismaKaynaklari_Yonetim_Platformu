import pytest

from core.exceptions import DuplicateRecordError, ResourceNotFoundError, ValidationError
from services.tag_service import TagService


def test_get_or_create_tag_creates_when_missing(session):
    tag = TagService(session).get_or_create_tag("Python")

    assert tag.id is not None
    assert tag.name == "python"


def test_get_or_create_tag_returns_existing(session):
    service = TagService(session)
    first = service.get_or_create_tag("Python")
    second = service.get_or_create_tag(" python ")

    assert second.id == first.id


def test_create_tag_rejects_duplicate(session):
    service = TagService(session)
    service.create_tag("Python")

    with pytest.raises(DuplicateRecordError):
        service.create_tag("python")


def test_create_tag_rejects_empty_name(session):
    with pytest.raises(ValidationError):
        TagService(session).create_tag("   ")


def test_update_tag_renames(session):
    service = TagService(session)
    tag = service.create_tag("Python")

    updated = service.update_tag(tag.id, "Django")

    assert updated.name == "django"


def test_update_tag_rejects_duplicate_name(session):
    service = TagService(session)
    service.create_tag("Python")
    other = service.create_tag("Rust")

    with pytest.raises(DuplicateRecordError):
        service.update_tag(other.id, "Python")


def test_update_tag_allows_keeping_own_name(session):
    service = TagService(session)
    tag = service.create_tag("Python")

    updated = service.update_tag(tag.id, "Python")

    assert updated.id == tag.id


def test_update_tag_not_found(session):
    with pytest.raises(ResourceNotFoundError):
        TagService(session).update_tag(999, "X")


def test_delete_tag_not_found(session):
    with pytest.raises(ResourceNotFoundError):
        TagService(session).delete_tag(999)


def test_get_all_returns_created_tags(session):
    service = TagService(session)
    service.create_tag("Python")
    service.create_tag("Rust")

    names = {t.name for t in service.get_all()}
    assert names == {"python", "rust"}
