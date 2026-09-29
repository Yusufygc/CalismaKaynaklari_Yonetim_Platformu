from datetime import timedelta

import pytest

from core.exceptions import DuplicateRecordError, ResourceNotFoundError, ValidationError
from services.saved_search_service import SavedSearchService, _utcnow


@pytest.fixture()
def service(session):
    return SavedSearchService(session)


def test_create_stores_clean_filters_and_seen_ids(service):
    search = service.create(
        "  transformer ",
        {"yearFrom": "2020", "openAccess": True, "workType": "", "language": None, "junk": "x"},
        tag_name=" Tez-Konusu ",
        seen_ids=["W1", "W2", "W1"],
    )

    assert search.topic == "transformer"
    assert search.filters == {"yearFrom": "2020", "openAccess": True}
    assert search.tag_name == "tez-konusu"
    assert search.seen_ids == ["W1", "W2"]
    assert search.new_count == 0 and search.last_checked_at is not None


def test_create_requires_topic_or_author(service):
    with pytest.raises(ValidationError):
        service.create("  ", {"yearFrom": "2020"})

    assert service.create("", {"authorId": "A1", "authorName": "Ada"}).id


def test_create_rejects_duplicate_ignoring_case_and_author_name(service):
    service.create("GAN", {"authorId": "A1", "authorName": "Ada"})

    with pytest.raises(DuplicateRecordError):
        service.create("gan", {"authorId": "A1", "authorName": "Ada Lovelace"})

    assert service.create("gan", {"authorId": "A2"}).id  # farkli filtre: farkli arama


def test_list_all_newest_first(service):
    first = service.create("a", None)
    second = service.create("b", None)

    assert [s.id for s in service.list_all()] == [second.id, first.id]


def test_delete_and_missing(service):
    search = service.create("a", None)

    service.delete(search.id)

    assert service.list_all() == []
    with pytest.raises(ResourceNotFoundError):
        service.delete(search.id)


def test_mark_seen_merges_newest_first_and_resets_counter(service):
    search = service.create("a", None, seen_ids=["W1"])
    service.record_check(search.id, 4)

    updated = service.mark_seen(search.id, ["W9", "W1"])

    assert updated.seen_ids == ["W9", "W1"]
    assert updated.new_count == 0


def test_mark_seen_caps_history(service):
    search = service.create("a", None)

    updated = service.mark_seen(search.id, [f"W{i}" for i in range(500)])

    assert len(updated.seen_ids) == 200 and updated.seen_ids[0] == "W0"


def test_record_check_sets_count(service):
    search = service.create("a", None)

    assert service.record_check(search.id, 3).new_count == 3
    assert service.record_check(search.id, -5).new_count == 0
    with pytest.raises(ResourceNotFoundError):
        service.record_check(999, 1)


def test_due_for_check_respects_age_and_never_checked(service):
    fresh = service.create("fresh", None)
    stale = service.create("stale", None)
    never = service.create("never", None)
    stale.last_checked_at = _utcnow() - timedelta(hours=3)
    never.last_checked_at = None
    service._session.commit()

    due = {s.id for s in service.due_for_check(timedelta(hours=1))}

    assert due == {stale.id, never.id} and fresh.id not in due
