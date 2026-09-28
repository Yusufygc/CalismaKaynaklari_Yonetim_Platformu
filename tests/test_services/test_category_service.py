import pytest

from core.exceptions import DuplicateRecordError, ResourceNotFoundError, ValidationError
from services.category_service import CategoryService


def test_create_category_success(session):
    category = CategoryService(session).create_category("Python", "#3776AB", "fa5s.code")

    assert category.id is not None
    assert category.name == "Python"
    assert category.color_hex == "#3776AB"
    assert category.icon == "fa5s.code"


@pytest.mark.parametrize("bad_hex", ["3776AB", "#3776A", "#GGGGGG", ""])
def test_create_category_rejects_invalid_hex(session, bad_hex):
    with pytest.raises(ValidationError):
        CategoryService(session).create_category("Python", bad_hex)


def test_create_category_rejects_duplicate_name(session):
    service = CategoryService(session)
    service.create_category("Python", "#3776AB")

    with pytest.raises(DuplicateRecordError):
        service.create_category("Python", "#000000")


def test_update_category_rejects_duplicate_name(session):
    service = CategoryService(session)
    service.create_category("Python", "#3776AB")
    other = service.create_category("Rust", "#DEA584")

    with pytest.raises(DuplicateRecordError):
        service.update_category(other.id, name="Python")


def test_update_category_allows_keeping_own_name(session):
    service = CategoryService(session)
    category = service.create_category("Python", "#3776AB")

    updated = service.update_category(category.id, name="Python", color_hex="#000000")

    assert updated.color_hex == "#000000"


def test_update_category_not_found(session):
    with pytest.raises(ResourceNotFoundError):
        CategoryService(session).update_category(999, name="X")


def test_delete_category_not_found(session):
    with pytest.raises(ResourceNotFoundError):
        CategoryService(session).delete_category(999)


def test_get_by_id_not_found(session):
    with pytest.raises(ResourceNotFoundError):
        CategoryService(session).get_by_id(999)


def test_get_all_returns_created_categories(session):
    service = CategoryService(session)
    service.create_category("Python", "#3776AB")
    service.create_category("Rust", "#DEA584")

    names = {c.name for c in service.get_all()}
    assert names == {"Python", "Rust"}


def test_validation_error_leaves_session_usable(session):
    service = CategoryService(session)

    with pytest.raises(ValidationError):
        service.create_category("Bad", "not-a-hex")

    category = service.create_category("Good", "#3776AB")
    assert category.id is not None
