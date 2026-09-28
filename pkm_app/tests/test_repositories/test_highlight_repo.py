from pkm_app.models import Highlight, Resource
from pkm_app.repositories.highlight_repo import HighlightRepository


def _make_resource(session, title="Test Kaynak") -> Resource:
    resource = Resource(title=title)
    session.add(resource)
    session.flush()
    return resource


def test_get_by_resource_scoped_and_newest_first(session):
    resource = _make_resource(session)
    repo = HighlightRepository(session)
    first = repo.create(Highlight(resource_id=resource.id, content="ilk"))
    second = repo.create(Highlight(resource_id=resource.id, content="ikinci"))

    results = repo.get_by_resource(resource.id)

    assert [h.id for h in results] == [second.id, first.id]


def test_get_by_resource_excludes_other_resources(session):
    resource_a = _make_resource(session, "A")
    resource_b = _make_resource(session, "B")
    repo = HighlightRepository(session)
    repo.create(Highlight(resource_id=resource_a.id, content="a"))
    repo.create(Highlight(resource_id=resource_b.id, content="b"))

    results = repo.get_by_resource(resource_a.id)

    assert [h.content for h in results] == ["a"]


def test_get_all_with_resource_eager_loads_resource(session):
    resource = _make_resource(session)
    repo = HighlightRepository(session)
    repo.create(Highlight(resource_id=resource.id, content="alinti"))
    session.commit()
    session.expire_all()

    results = repo.get_all_with_resource()

    assert len(results) == 1
    assert results[0].resource.title == "Test Kaynak"
