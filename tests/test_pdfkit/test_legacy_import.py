from datetime import datetime, timezone

import pytest

from models import Highlight, PdfNote, Resource, Vocabulary
from pdfkit.app.legacy_import import LegacyAnnotationImporter
from pdfkit.domain.annotations import STATUS_PENDING, STATUS_UNANCHORED, Segment


@pytest.fixture()
def importer(session):
    return LegacyAnnotationImporter(session)


def _highlight(session, resource_id, content="Hizli kahverengi tilki", color="#22C55E", page=0, start=10, length=22, comment=None):
    row = Highlight(
        resource_id=resource_id, content=content, color=color, page_number=page, start_index=start, length=length,
        comment=comment, created_at=datetime(2026, 9, 29, 10, 30, tzinfo=timezone.utc),
    )
    session.add(row)
    session.commit()
    return row


def test_pdf_highlights_are_moved_with_label_comment_and_timestamp_and_originals_are_deleted(
    session, annotations, importer, resource_with_document
):
    resource, document, _p = resource_with_document
    legacy = _highlight(session, resource.id, color="#06B6D4", comment="yontem")
    legacy_id = legacy.id

    report = importer.migrate()

    assert (report.copied, report.updated, report.removed) == (1, 0, 1)
    (moved,) = annotations.list_highlights(document.id)
    assert (moved.label_key, moved.color, moved.comment, moved.legacy_id) == ("method", "#06B6D4", "yontem", legacy_id)
    assert moved.status == STATUS_PENDING and moved.quote_prefix is None
    assert (moved.segments[0].page, moved.segments[0].start, moved.segments[0].end) == (0, 10, 32)
    assert moved.segments[0].text == "Hizli kahverengi tilki"
    assert (moved.created_at.year, moved.created_at.month, moved.created_at.day) == (2026, 9, 29)
    assert session.query(Highlight).count() == 0  # tek dogruluk kaynagi artik pdfkit


def test_highlights_without_a_pdf_document_or_without_position_stay_in_the_old_table(
    session, annotations, importer, resource_with_document
):
    resource, document, _p = resource_with_document
    html_only = Resource(title="Web yazisi", url="https://example.com/yazi")
    session.add(html_only)
    session.commit()
    _highlight(session, html_only.id)
    html_style = _highlight(session, resource.id)
    html_style.start_index = None  # HTML okuyucuda konumsuz alinti
    session.commit()

    report = importer.migrate()

    assert (report.copied, report.removed) == (0, 0)
    assert annotations.list_highlights(document.id) == []
    assert session.query(Highlight).count() == 2


def test_migration_is_idempotent(session, annotations, importer, resource_with_document):
    resource, document, _p = resource_with_document
    _highlight(session, resource.id)
    importer.migrate()

    again = importer.migrate()

    assert (again.copied, again.updated, again.removed) == (0, 0, 0)
    assert len(annotations.list_highlights(document.id)) == 1


def test_edits_made_in_the_old_ui_since_the_last_copy_are_applied_before_deleting(
    session, annotations, importer, resource_with_document
):
    """Onceki surumde bir kopya alinmis, sonra kullanici eski arayuzde yorum/renk degistirmis olabilir."""
    resource, document, _p = resource_with_document
    pdf_row = _highlight(session, resource.id, comment="ilk", color="#22C55E")
    importer._sync_highlights()  # onceki surumun kopyasi: eski satir yerinde kaliyor
    session.commit()
    pdf_row.comment, pdf_row.color = "guncel", "#EC4899"
    session.commit()

    report = importer.migrate()

    assert (report.copied, report.updated, report.removed) == (0, 1, 1)
    (moved,) = annotations.list_highlights(document.id)
    assert (moved.comment, moved.label_key) == ("guncel", "critique")


def test_natively_created_annotations_are_never_touched(session, annotations, importer, resource_with_document):
    resource, document, _p = resource_with_document
    native = annotations.create_highlight(document.id, "dogrudan pdfkit", [Segment(0, 1, 16, "dogrudan pdfkit")])

    importer.migrate()

    assert [a.id for a in annotations.list_highlights(document.id)] == [native.id]


def test_notes_and_terms_are_moved_and_originals_deleted(session, annotations, importer, resource_with_document):
    resource, document, _p = resource_with_document
    session.add_all(
        [
            PdfNote(resource_id=resource.id, page=2, x=10.0, y=20.0, note_text="Tekrar oku"),
            Vocabulary(resource_id=resource.id, word="ubiquitous", translation="her yerde", context_sentence="It is ubiquitous.", mastery_level=2),
        ]
    )
    session.commit()

    report = importer.migrate()

    assert (report.copied, report.removed) == (2, 2)
    (note,) = annotations.list_notes(document.id)
    assert (note.page, note.x, note.y, note.text) == (2, 10.0, 20.0, "Tekrar oku")
    (term,) = annotations.list_terms(document.id)
    assert (term.word, term.translation, term.context_sentence, term.mastery_level, term.status) == (
        "ubiquitous", "her yerde", "It is ubiquitous.", 2, STATUS_UNANCHORED,
    )
    assert session.query(PdfNote).count() == 0 and session.query(Vocabulary).count() == 0
