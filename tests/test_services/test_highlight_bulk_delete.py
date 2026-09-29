import pytest

from models import Highlight
from services.highlight_service import HighlightService
from services.resource_service import ResourceService
from services.schemas import ResourceCreateSchema


def _seed(session, count=4):
    resource = ResourceService(session).add_new_resource(ResourceCreateSchema(title="Kaynak"))
    service = HighlightService(session)
    return service, [service.create_highlight(resource.id, f"alinti {i}").id for i in range(count)]


def test_delete_highlights_removes_only_given_ids(session):
    service, ids = _seed(session)

    deleted = service.delete_highlights(ids[:3])

    assert deleted == 3
    remaining = session.query(Highlight).all()
    assert [h.id for h in remaining] == [ids[3]]


def test_delete_highlights_skips_missing_and_duplicate_ids(session):
    service, ids = _seed(session, 2)

    deleted = service.delete_highlights([ids[0], ids[0], 9999])

    assert deleted == 1
    assert session.query(Highlight).count() == 1


def test_delete_highlights_empty_list_is_noop(session):
    service, _ = _seed(session, 2)

    assert service.delete_highlights([]) == 0
    assert session.query(Highlight).count() == 2


def test_delete_highlights_rolls_back_everything_on_error(session, monkeypatch):
    service, ids = _seed(session, 3)
    real_delete = service._repo.delete

    def flaky(highlight_id):
        if highlight_id == ids[1]:
            raise RuntimeError("boom")
        return real_delete(highlight_id)

    monkeypatch.setattr(service._repo, "delete", flaky)

    with pytest.raises(RuntimeError):
        service.delete_highlights(ids)

    assert session.query(Highlight).count() == 3
