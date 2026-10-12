import time
from datetime import datetime, timezone

import pytest
from PySide6.QtPdf import QPdfDocument

from models import Highlight, Resource
from pdfkit.api import PdfBridge
from pdfkit.app.legacy_import import LegacyAnnotationImporter
from pdfkit.domain.annotations import STATUS_OK, STATUS_ORPHANED, Segment
from pdfkit.ui.models import AnnotationListModel
from pdfkit.ui.pdf_text import current_engine_fp
from pdfkit.ui.session import DocumentSession

POLYGON = [[(1.0, 2.0), (30.0, 2.0), (30.0, 12.0), (1.0, 12.0)]]


@pytest.fixture()
def session_under_test(pdf_library):
    model = AnnotationListModel()
    return DocumentSession(pdf_library, model), model


def _page_text(path):
    document = QPdfDocument()
    document.load(str(path))
    text = document.getSelectionAtIndex(0, 0, 100000).text()
    document.close()
    return text


def _legacy_highlight(session, resource_id, content, start, length):
    session.add(
        Highlight(
            resource_id=resource_id, content=content, color="#22C55E", page_number=0, start_index=start,
            length=length, created_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
        )
    )
    session.commit()


def test_open_without_a_pdf_document_fails_cleanly(session, session_under_test):
    plain = Resource(title="Web yazisi", url="https://example.com/yazi")
    session.add(plain)
    session.commit()
    pdf_session, model = session_under_test

    assert pdf_session.open(plain.id) is False
    assert not pdf_session.is_open and model.count == 0


def test_open_loads_annotations_and_completes_context_of_pending_legacy_rows(
    session, session_under_test, resource_with_document, pdf_library
):
    resource, document, path = resource_with_document
    text = _page_text(path)
    start = text.index("Hizli kahverengi tilki")
    _legacy_highlight(session, resource.id, "Hizli kahverengi tilki", start, 22)
    LegacyAnnotationImporter(session).run()
    pdf_session, model = session_under_test

    assert pdf_session.open(resource.id)

    assert pdf_session.document.id == document.id and model.count == 1
    (stored,) = pdf_library.annotations().list_highlights(document.id)
    assert stored.status == STATUS_OK and stored.quote_prefix.strip().endswith("Birinci cumle burada biter.")


def test_geometry_is_computed_lazily_per_page_persisted_and_not_repeated(
    session, session_under_test, resource_with_document, pdf_library
):
    resource, document, path = resource_with_document
    text = _page_text(path)
    start = text.index("tembel")
    annotations = pdf_library.annotations()
    created = annotations.create_highlight(document.id, "tembel", [Segment(0, start, start + 6, "tembel")])
    pdf_session, model = session_under_test
    pdf_session.open(resource.id)
    assert model.annotation(created.id).segments[0].polygons is None

    assert pdf_session.ensure_geometry(5) == 0  # baska sayfa: is yok
    assert pdf_session.ensure_geometry(0) == 1
    assert pdf_session.ensure_geometry(0) == 0  # tekrar hesaplanmaz

    stored = annotations.get_highlight(created.id)
    assert stored.segments[0].polygons and stored.engine_fp == current_engine_fp()
    assert model.annotation(created.id).segments[0].polygons == stored.segments[0].polygons
    pdf_session.close()
    reopened_session = DocumentSession(pdf_library, AnnotationListModel())
    reopened_session.open(resource.id)
    assert reopened_session.ensure_geometry(0) == 0  # sonraki acilista hesap yok (kalici)


def test_stale_engine_fingerprint_triggers_recomputation_and_orphans_are_skipped(
    session, session_under_test, resource_with_document, pdf_library
):
    resource, document, path = resource_with_document
    text = _page_text(path)
    start = text.index("tilki")
    annotations = pdf_library.annotations()
    stale = annotations.create_highlight(
        document.id, "tilki", [Segment(0, start, start + 5, "tilki", POLYGON)], engine_fp="qtpdf-0.0.1"
    )
    orphan = annotations.create_highlight(
        document.id, "yok olmus metin", [Segment(0, 1, 16, "yok olmus metin")], status=STATUS_ORPHANED
    )
    pdf_session, model = session_under_test
    pdf_session.open(resource.id)

    assert pdf_session.ensure_geometry(0) == 1

    refreshed = annotations.get_highlight(stale.id)
    assert refreshed.segments[0].polygons != POLYGON and refreshed.engine_fp == current_engine_fp()
    assert annotations.get_highlight(orphan.id).segments[0].polygons is None


def test_page_models_are_cached_per_page_and_cleared_on_close(session_under_test, resource_with_document, pdf_library):
    resource, document, _path = resource_with_document
    pdf_library.annotations().create_highlight(document.id, "tilki", [Segment(0, 1, 6, "tilki", POLYGON)])
    pdf_session, model = session_under_test
    pdf_session.open(resource.id)

    first = pdf_session.page_model(0)

    assert pdf_session.page_model(0) is first and first.rowCount() == 1
    assert pdf_session.page_model(1).rowCount() == 0
    pdf_session.close()
    assert model.count == 0 and not pdf_session.is_open
    assert pdf_session.ensure_geometry(0) == 0


def test_bridge_exposes_document_header_labels_and_page_models(session, resource_with_document, pdf_library):
    resource, document, path = resource_with_document
    pdf_library.annotations().create_highlight(
        document.id, "tilki", [Segment(0, 1, 6, "tilki", POLYGON)], engine_fp=current_engine_fp()
    )
    bridge = PdfBridge(pdf_library)
    changes = []
    bridge.currentDocumentChanged.connect(lambda: changes.append(1))

    assert bridge.openDocument(resource.id) is True

    header = bridge.currentDocument
    assert header["resourceId"] == resource.id and header["documentId"] == document.id
    assert header["pageCount"] == 1 and header["hasTextLayer"] is True and header["fileUrl"] == path.as_uri()
    assert bridge.annotations.count == 1 and bridge.pageModel(0).rowCount() == 1
    assert [label["key"] for label in bridge.labels][:2] == ["important", "finding"]
    assert bridge.ensureGeometry(0) == 0  # poligon saklanmis ve motor parmak izi guncel: hesap yok
    bridge.closeDocument()
    assert bridge.currentDocument == {} and bridge.annotations.count == 0
    assert len(changes) == 2


def test_opening_a_missing_document_clears_a_previously_open_one(session, resource_with_document, pdf_library):
    resource, _document, _path = resource_with_document
    plain = Resource(title="Web", url="https://example.com/x")
    session.add(plain)
    session.commit()
    bridge = PdfBridge(pdf_library)
    bridge.openDocument(resource.id)

    assert bridge.openDocument(plain.id) is False
    assert bridge.currentDocument == {}


def test_opening_a_document_with_a_thousand_annotations_stays_within_the_ui_budget(
    session, session_under_test, resource_with_document, pdf_library
):
    """Depolanmis geometri sayesinde acilis, alinti sayisindan bagimsiz olarak hizli (Faz 3 butcesi <=150 ms;
    CI makinelerinde dalgalanmaya karsi esik 4x gevsek)."""
    resource, document, _path = resource_with_document
    annotations = pdf_library.annotations()
    for i in range(1000):
        annotations.create_highlight(
            document.id, f"alinti metni {i}", [Segment(0, i, i + 10, f"alinti metni {i}", POLYGON)],
            engine_fp=current_engine_fp(),
        )
    pdf_session, model = session_under_test

    started = time.perf_counter()
    assert pdf_session.open(resource.id)
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert model.count == 1000
    assert elapsed_ms < 600, f"1000 alintili belge acilisi {elapsed_ms:.0f} ms"


def _legacy_like(annotations, document, count):
    for i in range(count):
        annotations.create_highlight(document.id, f"alinti {i:02d}", [Segment(0, 4 * i, 4 * i + 4, f"alinti {i:02d}")])


def test_geometry_of_many_legacy_annotations_is_computed_in_small_slices(
    qapp, session_under_test, resource_with_document, pdf_library
):
    from PySide6.QtTest import QTest

    from pdfkit.ui.session import GEOMETRY_CHUNK

    resource, document, _path = resource_with_document
    _legacy_like(pdf_library.annotations(), document, 20)
    pdf_session, model = session_under_test
    pdf_session.open(resource.id)

    first_slice = pdf_session.request_geometry(0)

    assert first_slice == GEOMETRY_CHUNK  # ilk dilim hemen, kalani olay dongusu turlarinda
    assert sum(1 for a in model.annotations_on_page(0) if a.segments[0].polygons) == GEOMETRY_CHUNK
    QTest.qWait(80)
    assert all(a.segments[0].polygons for a in model.annotations_on_page(0))


def test_pending_geometry_slices_stop_when_the_document_is_closed(
    qapp, session_under_test, resource_with_document, pdf_library
):
    from PySide6.QtTest import QTest

    resource, document, _path = resource_with_document
    _legacy_like(pdf_library.annotations(), document, 20)
    pdf_session, model = session_under_test
    pdf_session.open(resource.id)
    pdf_session.request_geometry(0)

    pdf_session.close()
    QTest.qWait(50)  # bekleyen dilimler kapali belgede calismamali (hata/cokme yok)

    assert model.count == 0
    persisted = [a for a in pdf_library.annotations().list_highlights(document.id) if a.segments[0].polygons]
    assert len(persisted) == 8
