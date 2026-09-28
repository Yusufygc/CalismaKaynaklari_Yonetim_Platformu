import pytest

from core.exceptions import ResourceNotFoundError, ValidationError
from models import PdfNote
from services.pdf_note_service import PdfNoteService
from services.resource_service import ResourceService
from services.schemas import ResourceCreateSchema


def _make_resource(session, title="Test Kaynak"):
    return ResourceService(session).add_new_resource(ResourceCreateSchema(title=title))


def test_create_note_persists_fields(session):
    resource = _make_resource(session)

    note = PdfNoteService(session).create_note(resource.id, page=2, x=100.5, y=200.25, note_text="onemli not")

    assert note.id is not None
    assert note.resource_id == resource.id
    assert note.page == 2
    assert note.x == 100.5
    assert note.y == 200.25
    assert note.note_text == "onemli not"


def test_create_note_rejects_empty_text(session):
    resource = _make_resource(session)

    with pytest.raises(ValidationError):
        PdfNoteService(session).create_note(resource.id, 0, 0.0, 0.0, "   ")


def test_create_note_rejects_unknown_resource(session):
    with pytest.raises(ResourceNotFoundError):
        PdfNoteService(session).create_note(999, 0, 0.0, 0.0, "not")


def test_update_note_changes_text(session):
    resource = _make_resource(session)
    note = PdfNoteService(session).create_note(resource.id, 0, 0.0, 0.0, "eski metin")

    updated = PdfNoteService(session).update_note(note.id, "yeni metin")

    assert updated.note_text == "yeni metin"
    assert session.get(PdfNote, note.id).note_text == "yeni metin"


def test_update_note_rejects_empty_text(session):
    resource = _make_resource(session)
    note = PdfNoteService(session).create_note(resource.id, 0, 0.0, 0.0, "metin")

    with pytest.raises(ValidationError):
        PdfNoteService(session).update_note(note.id, "  ")


def test_update_note_not_found(session):
    with pytest.raises(ResourceNotFoundError):
        PdfNoteService(session).update_note(999, "metin")


def test_get_by_resource_scoped_to_resource(session):
    resource_a = _make_resource(session, "A")
    resource_b = _make_resource(session, "B")
    service = PdfNoteService(session)
    service.create_note(resource_a.id, 0, 0.0, 0.0, "a notu")
    service.create_note(resource_b.id, 0, 0.0, 0.0, "b notu")

    results = service.get_by_resource(resource_a.id)

    assert [n.note_text for n in results] == ["a notu"]


def test_delete_note_removes_row(session):
    resource = _make_resource(session)
    note = PdfNoteService(session).create_note(resource.id, 0, 0.0, 0.0, "silinecek")

    PdfNoteService(session).delete_note(note.id)

    assert session.get(PdfNote, note.id) is None


def test_delete_note_not_found(session):
    with pytest.raises(ResourceNotFoundError):
        PdfNoteService(session).delete_note(999)


def test_deleting_resource_cascades_notes(session):
    resource = _make_resource(session)
    note = PdfNoteService(session).create_note(resource.id, 0, 0.0, 0.0, "cascade")

    ResourceService(session).delete_resource(resource.id)
    session.expire_all()

    assert session.get(PdfNote, note.id) is None
