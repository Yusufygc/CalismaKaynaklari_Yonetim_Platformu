import pytest

from pkm_app.core.exceptions import ResourceNotFoundError, ValidationError
from pkm_app.models import Vocabulary
from pkm_app.services.resource_service import ResourceService
from pkm_app.services.schemas import ResourceCreateSchema
from pkm_app.services.vocabulary_service import VocabularyService


def _make_resource(session, title="Test Kaynak"):
    return ResourceService(session).add_new_resource(ResourceCreateSchema(title=title))


def test_create_vocabulary_persists_fields(session):
    resource = _make_resource(session)

    vocab = VocabularyService(session).create_vocabulary(
        resource.id, "merhaba", "hello", context_sentence="Merhaba, nasilsin?"
    )

    assert vocab.id is not None
    assert vocab.resource_id == resource.id
    assert vocab.word == "merhaba"
    assert vocab.translation == "hello"
    assert vocab.context_sentence == "Merhaba, nasilsin?"
    assert vocab.mastery_level == 0


def test_create_vocabulary_rejects_empty_word(session):
    resource = _make_resource(session)

    with pytest.raises(ValidationError):
        VocabularyService(session).create_vocabulary(resource.id, "   ", "hello")


def test_create_vocabulary_rejects_empty_translation(session):
    resource = _make_resource(session)

    with pytest.raises(ValidationError):
        VocabularyService(session).create_vocabulary(resource.id, "merhaba", "  ")


def test_create_vocabulary_rejects_unknown_resource(session):
    with pytest.raises(ResourceNotFoundError):
        VocabularyService(session).create_vocabulary(999, "merhaba", "hello")


def test_get_by_resource_scoped_to_resource(session):
    resource_a = _make_resource(session, "A")
    resource_b = _make_resource(session, "B")
    service = VocabularyService(session)
    service.create_vocabulary(resource_a.id, "a", "a-translation")
    service.create_vocabulary(resource_b.id, "b", "b-translation")

    results = service.get_by_resource(resource_a.id)

    assert [v.word for v in results] == ["a"]


def test_get_all_returns_every_word(session):
    resource = _make_resource(session)
    service = VocabularyService(session)
    service.create_vocabulary(resource.id, "birinci", "first")
    service.create_vocabulary(resource.id, "ikinci", "second")

    assert {v.word for v in service.get_all()} == {"birinci", "ikinci"}


def test_delete_vocabulary_removes_row(session):
    resource = _make_resource(session)
    service = VocabularyService(session)
    vocab = service.create_vocabulary(resource.id, "silinecek", "to-delete")

    service.delete_vocabulary(vocab.id)

    assert session.get(Vocabulary, vocab.id) is None


def test_delete_vocabulary_not_found(session):
    with pytest.raises(ResourceNotFoundError):
        VocabularyService(session).delete_vocabulary(999)


def test_deleting_resource_cascades_vocabulary(session):
    resource = _make_resource(session)
    vocab = VocabularyService(session).create_vocabulary(resource.id, "cascade", "cascade-tr")

    ResourceService(session).delete_resource(resource.id)
    session.expire_all()

    assert session.get(Vocabulary, vocab.id) is None
