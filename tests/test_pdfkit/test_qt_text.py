"""Qt (QPdfDocument) tarafi: sayfa metni saglayicisi, secimden parca uretimi ve eski kayitlarin baglam tamamlamasi."""
from datetime import datetime, timezone

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtPdf import QPdfDocument

from models import Highlight
from pdfkit.app.legacy_import import LegacyAnnotationImporter
from pdfkit.domain.annotations import STATUS_OK, STATUS_ORPHANED
from pdfkit.ui.pdf_text import QtPageTextProvider, current_engine_fp, segment_from_selection
from tests.test_pdfkit.conftest import SENTENCE


@pytest.fixture()
def qdoc(qapp, resource_with_document):
    _resource, _document, path = resource_with_document
    document = QPdfDocument()
    document.load(str(path))
    assert document.status() == QPdfDocument.Status.Ready
    return document


def test_provider_exposes_qt_page_text_and_page_count(qdoc):
    provider = QtPageTextProvider(qdoc)

    assert provider.page_count() == 1
    assert SENTENCE in " ".join(provider.text_of(0).split())
    assert current_engine_fp().startswith("qtpdf-")


def test_segment_from_selection_carries_indices_text_and_cached_geometry(qdoc):
    text = qdoc.getSelectionAtIndex(0, 0, 100000).text()
    start = text.index("tilki")
    first = qdoc.getSelectionAtIndex(0, start, 1).boundingRectangle()
    last = qdoc.getSelectionAtIndex(0, start + 4, 1).boundingRectangle()

    selection = qdoc.getSelection(0, QPointF(first.center()), QPointF(last.right(), last.center().y()))  # son harfin sag kenari
    segment = segment_from_selection(0, selection)

    assert segment.text.strip() == "tilki" and segment.page == 0
    assert text[segment.start : segment.end].strip() == "tilki"
    assert segment.polygons  # secim aninda hazir: sonradan getSelectionAtIndex gerekmez
    again = qdoc.getSelectionAtIndex(0, segment.start, segment.end - segment.start)
    assert segment.polygons == [[(p.x(), p.y()) for p in polygon] for polygon in again.bounds()]


def _legacy(session, resource_id, content, start, length):
    row = Highlight(
        resource_id=resource_id, content=content, color="#22C55E", page_number=0, start_index=start, length=length,
        created_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
    )
    session.add(row)
    session.commit()


def test_backfill_verifies_position_extracts_context_and_recovers_shifted_or_lost_anchors(
    session, annotations, qdoc, resource_with_document
):
    resource, document, _path = resource_with_document
    text = qdoc.getSelectionAtIndex(0, 0, 100000).text()
    real = text.index("Hizli kahverengi tilki")
    _legacy(session, resource.id, "Hizli kahverengi tilki", real, 22)  # konum dogru
    _legacy(session, resource.id, "tembel kopegin ustunden", text.index("tembel") + 9, 23)  # eski motorun kaymis indeksi
    _legacy(session, resource.id, "bu metin belgede hic yok", 5, 24)  # kayip
    LegacyAnnotationImporter(session).migrate()

    report = annotations.backfill_context(document.id, QtPageTextProvider(qdoc), current_engine_fp())

    assert (report.resolved, report.moved, report.orphaned) == (2, 1, 1)
    by_quote = {a.quote_exact: a for a in annotations.list_highlights(document.id)}
    exact, shifted, lost = by_quote["Hizli kahverengi tilki"], by_quote["tembel kopegin ustunden"], by_quote["bu metin belgede hic yok"]
    assert exact.status == STATUS_OK and exact.quote_prefix.strip().endswith("Birinci cumle burada biter.")
    assert exact.engine_fp == current_engine_fp() and exact.quote_suffix
    assert shifted.status == STATUS_OK
    assert text[shifted.segments[0].start : shifted.segments[0].end].strip() == "tembel kopegin ustunden"
    assert lost.status == STATUS_ORPHANED

    again = annotations.backfill_context(document.id, QtPageTextProvider(qdoc), current_engine_fp())
    assert (again.resolved, again.orphaned) == (0, 0)  # yalniz bekleyenler islenir
