from pkm_app.models import Resource, Vocabulary
from pkm_app.repositories.vocabulary_repo import VocabularyRepository


def _make_resource(session, title="Test Kaynak") -> Resource:
    resource = Resource(title=title)
    session.add(resource)
    session.flush()
    return resource


def test_get_by_resource_scoped_and_newest_first(session):
    resource = _make_resource(session)
    repo = VocabularyRepository(session)
    first = repo.create(Vocabulary(resource_id=resource.id, word="ilk", translation="first"))
    second = repo.create(Vocabulary(resource_id=resource.id, word="ikinci", translation="second"))

    results = repo.get_by_resource(resource.id)

    assert [v.id for v in results] == [second.id, first.id]


def test_get_by_resource_excludes_other_resources(session):
    resource_a = _make_resource(session, "A")
    resource_b = _make_resource(session, "B")
    repo = VocabularyRepository(session)
    repo.create(Vocabulary(resource_id=resource_a.id, word="a", translation="a-tr"))
    repo.create(Vocabulary(resource_id=resource_b.id, word="b", translation="b-tr"))

    results = repo.get_by_resource(resource_a.id)

    assert [v.word for v in results] == ["a"]


def test_get_all_with_resource_eager_loads_resource(session):
    resource = _make_resource(session)
    repo = VocabularyRepository(session)
    repo.create(Vocabulary(resource_id=resource.id, word="kelime", translation="word"))
    session.commit()
    session.expire_all()

    results = repo.get_all_with_resource()

    assert len(results) == 1
    assert results[0].resource.title == "Test Kaynak"
