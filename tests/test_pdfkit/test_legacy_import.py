from datetime import datetime, timezone

import pytest

from models import Highlight, PdfNote, Resource, Vocabulary
from pdfkit.app.legacy_import import LegacyAnnotationImporter
from pdfkit.domain.annotations import STATUS_PENDING, STATUS_UNANCHORED


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


def test_pdf_highlights_are_copied_with_label_comment_and_timestamp(session, annotations, importer, resource_with_document):
    resource, document, _p = resource_with_document
    legacy = _highlight(session, resource.id, color="#06B6D4", comment="yontem")

    report = importer.run()

    assert (report.added, report.updated, report.removed) == (1, 0, 0)
    (copied,) = annotations.list_highlights(document.id)
    assert (copied.label_key, copied.color, copied.comment, copied.legacy_id) == ("method", "#06B6D4", "yontem", legacy.id)
    assert copied.status == STATUS_PENDING and copied.quote_prefix is None
    assert (copied.segments[0].page, copied.segments[0].start, copied.segments[0].end) == (0, 10, 32)
    assert copied.segments[0].text == "Hizli kahverengi tilki"
    assert (copied.created_at.year, copied.created_at.month, copied.created_at.day) == (2026, 9, 29)


def test_highlights_without_a_pdf_document_or_without_position_stay_in_the_old_table(session, annotations, importer, resource_with_document):
    resource, document, _p = resource_with_document
    html_only = Resource(title="Web yazisi", url="https://example.com/yazi")
    session.add(html_only)
    session.commit()
    _highlight(session, html_only.id)
    html_style = _highlight(session, resource.id)
    html_style.start_index = None  # HTML okuyucuda konumsuz alinti
    session.commit()

    assert importer.run().added == 0
    assert annotations.list_highlights(document.id) == []


def test_run_is_idempotent_and_mirrors_legacy_edits_and_deletions(session, annotations, importer, resource_with_document):
    resource, document, _p = resource_with_document
    keep = _highlight(session, resource.id, comment="ilk")
    drop = _highlight(session, resource.id, content="Silinecek alinti metni", start=40)
    importer.run()
    assert importer.run().added == 0  # ikinci calistirma: degisiklik yok

    keep.comment, keep.color = "guncel", "#EC4899"
    session.delete(drop)
    session.commit()
    report = importer.run()

    assert (report.added, report.updated, report.removed) == (0, 1, 1)
    (remaining,) = annotations.list_highlights(document.id)
    assert (remaining.comment, remaining.label_key) == ("guncel", "critique")


def test_natively_created_annotations_are_never_touched(session, annotations, importer, resource_with_document):
    from pdfkit.domain.annotations import Segment

    resource, document, _p = resource_with_document
    native = annotations.create_highlight(document.id, "dogrudan pdfkit", [Segment(0, 1, 16, "dogrudan pdfkit")])

    importer.run(delete_missing=True)

    assert [a.id for a in annotations.list_highlights(document.id)] == [native.id]


def test_notes_and_terms_are_copied_and_synced(session, annotations, importer, resource_with_document):
    resource, document, _p = resource_with_document
    session.add_all(
        [
            PdfNote(resource_id=resource.id, page=2, x=10.0, y=20.0, note_text="Tekrar oku"),
            Vocabulary(resource_id=resource.id, word="ubiquitous", translation="her yerde", context_sentence="It is ubiquitous.", mastery_level=2),
        ]
    )
    session.commit()

    report = importer.run()

    assert report.added == 2
    (note,) = annotations.list_notes(document.id)
    assert (note.page, note.x, note.y, note.text) == (2, 10.0, 20.0, "Tekrar oku")
    (term,) = annotations.list_terms(document.id)
    assert (term.word, term.translation, term.context_sentence, term.mastery_level, term.status) == (
        "ubiquitous", "her yerde", "It is ubiquitous.", 2, STATUS_UNANCHORED,
    )

    session.query(Vocabulary).delete()
    session.commit()
    assert importer.run().removed == 1
    assert annotations.list_terms(document.id) == []
