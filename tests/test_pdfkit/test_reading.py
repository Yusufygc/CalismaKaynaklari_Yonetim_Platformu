"""Okuma durumu (K14): kaldigi yer, en uzak sayfa, aktif sure ve kart ilerlemesi."""
from datetime import datetime, timedelta, timezone

import pytest
from PySide6.QtTest import QTest

from models import Resource
from pdfkit.api import PdfBridge
from pdfkit.app.documents import DocumentService
from pdfkit.app.importing import prepare_pdf
from pdfkit.app.reading import ReadingService
from pdfkit.domain.errors import NotFoundError
from pdfkit.domain.reading import ACTIVE_GAP_SECONDS, progress_ratio
from tests.pdf_factory import write_outline_pdf

T0 = datetime(2026, 10, 13, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def five_page_document(session, pdf_store, tmp_path):
    source = write_outline_pdf(tmp_path / "bes-sayfa.pdf", ["A", "B", "C", "D", "E"])
    prepared = prepare_pdf(source, pdf_store)
    resource = Resource(title="Bes sayfa", url=pdf_store.absolute(prepared.stored.rel_path).as_uri())
    session.add(resource)
    session.commit()
    document = DocumentService(session, pdf_store).register(prepared, resource.id, "local")
    return resource, document


@pytest.fixture()
def reading(session):
    return ReadingService(session)


def test_progress_ratio_counts_the_furthest_page_inclusively_and_stays_in_range():
    assert progress_ratio(0, 10) == 0.1
    assert progress_ratio(9, 10) == 1.0
    assert progress_ratio(50, 10) == 1.0
    assert progress_ratio(0, 0) == 0.0


def test_first_save_creates_the_state_and_get_returns_it(reading, five_page_document):
    _resource, document = five_page_document
    assert reading.get(document.id) is None

    saved = reading.save(document.id, 2, 12.5, 40.0, 1.5, now=T0)

    assert reading.get(document.id) == saved
    assert (saved.last_page, saved.loc_x, saved.loc_y, saved.zoom) == (2, 12.5, 40.0, 1.5)
    assert saved.max_page == 2 and saved.total_seconds == 0


def test_values_are_clamped_and_non_finite_numbers_fall_back(reading, five_page_document):
    _resource, document = five_page_document

    high = reading.save(document.id, 99, -5.0, float("nan"), 500.0, now=T0)
    low = reading.save(document.id, -3, 0.0, 0.0, 0.0, now=T0 + timedelta(seconds=1))
    bad_zoom = reading.save(document.id, 0, 0.0, 0.0, float("inf"), now=T0 + timedelta(seconds=2))

    assert high.last_page == 4 and high.zoom == 10.0 and high.loc_x == 0.0 and high.loc_y == 0.0
    assert low.last_page == 0 and low.zoom == 0.1
    assert bad_zoom.zoom == 1.0


def test_furthest_page_never_decreases_when_the_reader_goes_back(reading, five_page_document):
    _resource, document = five_page_document
    reading.save(document.id, 3, 0, 0, 1.0, now=T0)

    back = reading.save(document.id, 1, 0, 0, 1.0, now=T0 + timedelta(seconds=5))

    assert back.last_page == 1 and back.max_page == 3


def test_seen_page_drives_progress_while_the_resume_point_stays_at_the_view_top(reading, five_page_document):
    _resource, document = five_page_document

    state = reading.save(document.id, 3, 0, 0, 1.0, seen_page=4, now=T0)  # son sayfa hic ustte olmayabilir
    clamped = reading.save(document.id, 3, 0, 0, 1.0, seen_page=99, now=T0 + timedelta(seconds=1))

    assert (state.last_page, state.max_page) == (3, 4)
    assert clamped.max_page == 4


def test_active_time_adds_short_gaps_and_caps_long_idle_periods(reading, five_page_document):
    _resource, document = five_page_document
    reading.save(document.id, 0, 0, 0, 1.0, now=T0)

    reading.save(document.id, 1, 0, 0, 1.0, now=T0 + timedelta(seconds=20))  # aktif: +20
    after_idle = reading.save(document.id, 2, 0, 0, 1.0, now=T0 + timedelta(hours=3))  # bosta: +ust sinir

    assert after_idle.total_seconds == 20 + ACTIVE_GAP_SECONDS


def test_unknown_document_is_rejected(reading):
    with pytest.raises(NotFoundError):
        reading.save(9999, 0, 0, 0, 1.0)


def test_progress_map_covers_only_resources_with_state(reading, session, five_page_document, pdf_store, tmp_path):
    resource, document = five_page_document
    other_source = write_outline_pdf(tmp_path / "diger.pdf", ["X", "Y"])
    prepared = prepare_pdf(other_source, pdf_store)
    other = Resource(title="Diger", url=pdf_store.absolute(prepared.stored.rel_path).as_uri())
    session.add(other)
    session.commit()
    DocumentService(session, pdf_store).register(prepared, other.id, "local")

    reading.save(document.id, 1, 0, 0, 1.0, now=T0)  # 2 / 5

    assert reading.progress_map() == {resource.id: pytest.approx(0.4)}


def test_deleting_the_document_removes_its_reading_state(reading, session, five_page_document, pdf_store):
    resource, document = five_page_document
    reading.save(document.id, 1, 0, 0, 1.0, now=T0)
    session.delete(resource)
    session.commit()

    DocumentService(session, pdf_store).collect_garbage()

    assert reading.get(document.id) is None


# ---- Bridge: gecikmeli kayit, kapanista yazma, yeniden acilista geri yukleme ----


@pytest.fixture()
def bridge(pdf_library):
    return PdfBridge(pdf_library)


def test_state_is_empty_on_first_open_and_restored_after_close_and_reopen(bridge, five_page_document):
    resource, _document = five_page_document
    assert bridge.openDocument(resource.id)
    assert bridge.readingState["hasState"] is False

    bridge.saveReadingState(3, 10.0, 20.0, 1.25, 3)
    bridge.closeDocument()  # kapanista anında yazilir (zamanlayici beklenmez)
    assert bridge.readingState["hasState"] is False

    bridge.openDocument(resource.id)
    assert bridge.readingState == {"hasState": True, "page": 3, "x": 10.0, "y": 20.0, "zoom": 1.25}


def test_saves_are_merged_into_one_delayed_write_and_announce_progress(bridge, five_page_document):
    resource, document = five_page_document
    announced = []
    bridge.readingProgressChanged.connect(announced.append)
    bridge.openDocument(resource.id)

    for page in range(4):
        bridge.saveReadingState(page, 0.0, 0.0, 1.0, page)
    assert bridge._library.reading().get(document.id) is None  # henuz yazilmadi: UI yolunu bloklamaz
    QTest.qWait(1300)

    assert announced == [resource.id]
    assert bridge._library.reading().get(document.id).last_page == 3


def test_saving_without_an_open_document_is_ignored(bridge, five_page_document):
    _resource, document = five_page_document

    bridge.saveReadingState(2, 0.0, 0.0, 1.0, 2)
    bridge.closeDocument()

    assert bridge._library.reading().get(document.id) is None


def test_switching_documents_flushes_the_pending_state_of_the_previous_one(bridge, five_page_document, session, pdf_store, tmp_path):
    resource, document = five_page_document
    other_prepared = prepare_pdf(write_outline_pdf(tmp_path / "diger.pdf", ["X", "Y"]), pdf_store)
    other = Resource(title="Diger", url=pdf_store.absolute(other_prepared.stored.rel_path).as_uri())
    session.add(other)
    session.commit()
    DocumentService(session, pdf_store).register(other_prepared, other.id, "local")
    bridge.openDocument(resource.id)
    bridge.saveReadingState(4, 0.0, 0.0, 1.0, 4)

    bridge.openDocument(other.id)

    assert bridge._library.reading().get(document.id).last_page == 4
    assert bridge.readingState["hasState"] is False
