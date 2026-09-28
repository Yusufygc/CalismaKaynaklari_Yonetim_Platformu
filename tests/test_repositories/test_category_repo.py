from models import Category
from repositories.category_repo import CategoryRepository


def test_get_by_name_finds_exact_match(session):
    repo = CategoryRepository(session)
    repo.create(Category(name="Python", color_hex="#3776AB"))

    found = repo.get_by_name("Python")
    assert found is not None
    assert found.name == "Python"


def test_get_by_name_is_case_sensitive(session):
    repo = CategoryRepository(session)
    repo.create(Category(name="Python", color_hex="#3776AB"))

    assert repo.get_by_name("python") is None


def test_get_by_name_returns_none_when_missing(session):
    repo = CategoryRepository(session)

    assert repo.get_by_name("Missing") is None
