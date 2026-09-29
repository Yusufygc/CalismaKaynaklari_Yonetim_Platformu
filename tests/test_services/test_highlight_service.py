import pytest

from core.exceptions import ResourceNotFoundError, ValidationError
from models import Highlight
from services.highlight_service import HighlightService
from services.resource_service import ResourceService
from services.schemas import ResourceCreateSchema


def _make_resource(session, title="Test Kaynak"):
    return ResourceService(session).add_new_resource(ResourceCreateSchema(title=title))


def test_create_highlight_persists_fields(session):
    resource = _make_resource(session)

    highlight = HighlightService(session).create_highlight(
        resource.id, "onemli bir alinti", color="#FDE68A"
    )

    assert highlight.id is not None
    assert highlight.resource_id == resource.id
    assert highlight.content == "onemli bir alinti"
    assert highlight.color == "#FDE68A"


def test_create_highlight_persists_pdf_position(session):
    resource = _make_resource(session)

    highlight = HighlightService(session).create_highlight(
        resource.id, "pdf alintisi", color="#EAB308", page=3, start_index=120, length=45
    )

    assert highlight.page_number == 3
    assert highlight.start_index == 120
    assert highlight.length == 45


def test_update_highlight_color_changes_color(session):
    resource = _make_resource(session)
    highlight = HighlightService(session).create_highlight(resource.id, "renk degisecek", color="#EAB308")

    updated = HighlightService(session).update_highlight_color(highlight.id, "#22C55E")

    assert updated.color == "#22C55E"
    assert session.get(Highlight, highlight.id).color == "#22C55E"


def test_update_highlight_comment_sets_and_clears(session):
    resource = _make_resource(session)
    service = HighlightService(session)
    highlight = service.create_highlight(resource.id, "alinti", color="#EAB308")

    updated = service.update_highlight_comment(highlight.id, "  yontem kismi, tekrar bak  ")
    assert updated.comment == "yontem kismi, tekrar bak"

    cleared = service.update_highlight_comment(highlight.id, "   ")
    assert cleared.comment is None


def test_update_highlight_comment_not_found(session):
    with pytest.raises(ResourceNotFoundError):
        HighlightService(session).update_highlight_comment(999, "x")


def test_label_for_color_maps_palette_and_falls_back():
    from core.constants.highlight_labels import label_for_color

    assert label_for_color("#22c55e") == "Bulgu / Sonuç"
    assert label_for_color("#EAB308") == "Önemli"
    assert label_for_color("#123456") == "Genel"
    assert label_for_color(None) == "Genel"


def test_update_highlight_color_not_found(session):
    with pytest.raises(ResourceNotFoundError):
        HighlightService(session).update_highlight_color(999, "#22C55E")


def test_create_highlight_rejects_empty_content(session):
    resource = _make_resource(session)

    with pytest.raises(ValidationError):
        HighlightService(session).create_highlight(resource.id, "   ")


def test_create_highlight_rejects_unknown_resource(session):
    with pytest.raises(ResourceNotFoundError):
        HighlightService(session).create_highlight(999, "alinti")


def test_get_by_resource_scoped_to_resource(session):
    resource_a = _make_resource(session, "A")
    resource_b = _make_resource(session, "B")
    service = HighlightService(session)
    service.create_highlight(resource_a.id, "a alintisi")
    service.create_highlight(resource_b.id, "b alintisi")

    results = service.get_by_resource(resource_a.id)

    assert [h.content for h in results] == ["a alintisi"]


def test_get_all_returns_every_highlight(session):
    resource = _make_resource(session)
    service = HighlightService(session)
    service.create_highlight(resource.id, "birinci")
    service.create_highlight(resource.id, "ikinci")

    assert {h.content for h in service.get_all()} == {"birinci", "ikinci"}


def test_delete_highlight_removes_row(session):
    resource = _make_resource(session)
    service = HighlightService(session)
    highlight = service.create_highlight(resource.id, "silinecek")

    service.delete_highlight(highlight.id)

    assert session.get(Highlight, highlight.id) is None


def test_delete_highlight_not_found(session):
    with pytest.raises(ResourceNotFoundError):
        HighlightService(session).delete_highlight(999)


def test_deleting_resource_cascades_highlights(session):
    resource = _make_resource(session)
    highlight = HighlightService(session).create_highlight(resource.id, "cascade")

    ResourceService(session).delete_resource(resource.id)
    session.expire_all()

    assert session.get(Highlight, highlight.id) is None
