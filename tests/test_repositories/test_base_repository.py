from models import Category
from repositories.base_repository import BaseRepository


def test_create_assigns_id(session):
    repo = BaseRepository(Category, session)
    category = repo.create(Category(name="Python", color_hex="#3776AB"))

    assert category.id is not None


def test_get_by_id_returns_none_when_missing(session):
    repo = BaseRepository(Category, session)

    assert repo.get_by_id(999) is None


def test_get_all_returns_created_records(session):
    repo = BaseRepository(Category, session)
    repo.create(Category(name="Python", color_hex="#3776AB"))
    repo.create(Category(name="Rust", color_hex="#DEA584"))

    assert len(repo.get_all()) == 2


def test_delete_returns_false_when_missing(session):
    repo = BaseRepository(Category, session)

    assert repo.delete(999) is False


def test_delete_returns_true_and_removes_record(session):
    repo = BaseRepository(Category, session)
    category = repo.create(Category(name="Python", color_hex="#3776AB"))

    assert repo.delete(category.id) is True
    assert repo.get_by_id(category.id) is None
