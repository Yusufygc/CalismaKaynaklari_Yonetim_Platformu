from models import Tag
from repositories.tag_repo import TagRepository


def test_get_by_name_lowercases_lookup(session):
    repo = TagRepository(session)
    repo.create(Tag(name="python"))

    assert repo.get_by_name("Python") is not None
    assert repo.get_by_name("PYTHON") is not None


def test_get_by_name_returns_none_when_missing(session):
    repo = TagRepository(session)

    assert repo.get_by_name("missing") is None
