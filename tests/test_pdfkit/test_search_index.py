"""Tam metin dizini: yazma/okuma, Turkce arama, yarim dizin, yetim temizligi ve arka plan indeksleyici (gercek PDF'ler)."""
import pytest
from PySide6.QtTest import QTest
from sqlalchemy import delete

from models import Resource
from pdfkit.api import PdfLibrary, TextIndexer
from pdfkit.app.documents import DocumentService
from pdfkit.app.importing import prepare_pdf
from pdfkit.app.search import INDEX_VERSION, IndexService, SearchService
from pdfkit.infra.orm import PdfDocumentRow, PdfResourceLinkRow
from pdfkit.infra.search_repository import STATUS_FAILED, STATUS_INDEXING, STATUS_NO_TEXT, STATUS_OK, PageIndexRepository
from tests.pdf_factory import write_multipage_text_pdf, write_outline_pdf
from tests.test_pdfkit.conftest import NullCatalog

PAGES = [
    ["Kuantum bilgisayarlar hakkinda giris bolumu. Bu makale temel kavramlari anlatir."],
    ["Ikinci sayfa: cocuklarin ogrenme sekli ve motivasyon uzerine bir tartisma."],
    ["Ucuncu sayfa sonuc bolumudur. Kuantum ustunlugu tartisilmaya devam ediyor."],
]


class _InlinePool:
    def start(self, worker):
        worker.run()


class _DeferredPool:
    """Isleri biriktirir; test istedigi zaman calistirir (iptal denemeleri icin)."""

    def __init__(self):
        self.jobs = []

    def start(self, worker):
        self.jobs.append(worker)

    def run_all(self):
        jobs, self.jobs = self.jobs, []
        for job in jobs:
            job.run()


def _add(session, pdf_store, tmp_path, name, pages):
    prepared = prepare_pdf(write_multipage_text_pdf(tmp_path / f"{name}.pdf", pages), pdf_store)
    resource = Resource(title=name, url=pdf_store.absolute(prepared.stored.rel_path).as_uri())
    session.add(resource)
    session.commit()
    return DocumentService(session, pdf_store).register(prepared, resource.id, "local")


@pytest.fixture()
def library(qapp, session, pdf_store):
    return PdfLibrary(session, lambda: pdf_store.root, NullCatalog(), lambda: _InlinePool(), lambda url: None)


@pytest.fixture()
def document(session, pdf_store, tmp_path):
    return _add(session, pdf_store, tmp_path, "kuantum", PAGES)


def _index(session, document_id, pages):
    service = IndexService(session)
    assert service.available()
    service.begin(document_id)
    service.add_pages(document_id, 0, pages)
    service.finish(document_id, len(pages))


def _wait(indexer, timeout=5000):
    waited = 0
    while indexer.status()["state"] == "running" or indexer.status()["pending"]:
        QTest.qWait(10)
        waited += 10
        assert waited < timeout, indexer.status()


# ---- servis ----


def test_the_index_table_is_created_when_missing_and_search_finds_indexed_pages(session, document):
    _index(session, document.id, [" ".join(p) for p in PAGES])

    hits = SearchService(session).search("kuantum")

    assert [(h.document_id, h.page) for h in sorted(hits, key=lambda h: h.page)] == [(document.id, 0), (document.id, 2)]
    assert all("Kuantum" in h.snippet.text for h in hits) and all(h.snippet.spans for h in hits)


def test_turkish_letters_and_case_do_not_matter_and_prefixes_match(session, document):
    _index(session, document.id, [" ".join(p) for p in PAGES])
    search = SearchService(session)

    assert [h.page for h in search.search("COCUKLARIN ÖĞRENME")] == [1]
    assert [h.page for h in search.search("ogrenme sek")] == [1]  # son sözcük önek
    assert [h.page for h in search.search('"sonuc bolumudur"')] == [2]
    assert search.search("yokboyleKelime") == [] and search.search("") == [] and search.search("***") == []


def test_a_document_is_not_searchable_until_its_index_is_complete(session, document):
    service = IndexService(session)
    assert service.available()
    service.begin(document.id)
    service.add_pages(document.id, 0, ["kuantum sayfasi"])

    assert SearchService(session).search("kuantum") == []  # yarim dizin
    service.finish(document.id, 1)
    assert len(SearchService(session).search("kuantum")) == 1


def test_reindexing_replaces_the_old_pages_and_other_documents_are_untouched(session, pdf_store, tmp_path, document):
    other = _add(session, pdf_store, tmp_path, "baska", [["kuantum baska belge ve yeterince uzun bir metin cumlesi"]])
    _index(session, document.id, ["eski metin kuantum", "ikinci"])
    _index(session, other.id, ["kuantum baska belge"])

    _index(session, document.id, ["yeni metin"])

    search = SearchService(session)
    assert {h.document_id for h in search.search("kuantum")} == {other.id}
    assert [h.document_id for h in search.search("yeni")] == [document.id]
    repo = PageIndexRepository(session)
    assert repo.page_row_count(document.id) == 1 and repo.page_row_count(other.id) == 1


def test_orphan_rows_of_deleted_documents_are_purged_and_never_returned(session, pdf_store, tmp_path, document):
    other = _add(session, pdf_store, tmp_path, "baska", [["kuantum baska belge ve yeterince uzun bir metin cumlesi"]])
    _index(session, document.id, ["kuantum bir"])
    _index(session, other.id, ["kuantum iki"])
    session.execute(delete(PdfResourceLinkRow).where(PdfResourceLinkRow.document_id == document.id))
    session.execute(delete(PdfDocumentRow).where(PdfDocumentRow.id == document.id))  # FK cascade durum satirini siler
    session.commit()

    assert [h.document_id for h in SearchService(session).search("kuantum")] == [other.id]
    removed = IndexService(session).purge_orphans()

    repo = PageIndexRepository(session)
    assert removed == 1 and repo.page_row_count() == 1 and repo.page_row_count(other.id) == 1


def test_documents_needing_an_index_follow_state_and_version(session, document):
    repo = PageIndexRepository(session)
    service = IndexService(session)
    assert service.available() and service.pending() == [document.id]

    service.begin(document.id)
    assert service.pending() == [document.id]  # yarim kalmis: yeniden
    service.finish(document.id, 3)
    assert service.pending() == []
    repo.set_state(document.id, STATUS_OK, 3, INDEX_VERSION - 1)
    assert service.pending() == [document.id]  # eski surum
    service.fail(document.id)
    assert service.pending() == [] and repo.state(document.id).status == STATUS_FAILED  # basarisiz belge her acilista denenmez
    service.finish_without_text(document.id)
    assert repo.state(document.id).status == STATUS_NO_TEXT


def test_documents_without_a_text_layer_are_never_pending(session, pdf_store, tmp_path):
    prepared = prepare_pdf(write_outline_pdf(tmp_path / "bos.pdf", ["A", "B"]), pdf_store)
    resource = Resource(title="bos", url=pdf_store.absolute(prepared.stored.rel_path).as_uri())
    session.add(resource)
    session.commit()
    document = DocumentService(session, pdf_store).register(prepared, resource.id, "local")

    assert not document.has_text_layer
    assert IndexService(session).available() and IndexService(session).pending() == []


def test_blank_and_surrogate_pages_are_handled(session, document):
    service = IndexService(session)
    assert service.available()
    service.begin(document.id)

    added = service.add_pages(document.id, 0, ["", "   ", "bozuk \ud800 karakter kuantum"])
    service.finish(document.id, 3)

    assert added == 1
    assert [h.page for h in SearchService(session).search("kuantum")] == [2]


# ---- arka plan indeksleyici ----


def test_scan_indexes_every_pending_document_in_the_background(library, session, pdf_store, tmp_path, document):
    second = _add(session, pdf_store, tmp_path, "ikinci", [["farkli bir belge hakkinda yeterince uzun bir metin var burada"], ["kuantum burada da geciyor ve yeterince uzun bir cumle"]])
    indexer = TextIndexer(library, lambda: _InlinePool(), write_chunk=1)
    done = []
    indexer.finished.connect(lambda: done.append(1))

    indexer.scan()
    _wait(indexer)
    QTest.qWait(30)

    hits = library.searching().search("kuantum")
    assert {(h.document_id, h.page) for h in hits} == {(document.id, 0), (document.id, 2), (second.id, 1)}
    assert indexer.status() == {"state": "idle", "done": 2, "total": 2, "pending": 0} and done
    assert library.indexing().pending() == []


def test_writes_are_done_in_small_slices_so_the_ui_thread_is_not_blocked(library, session, pdf_store, tmp_path, monkeypatch):
    many = _add(session, pdf_store, tmp_path, "uzun", [[f"sayfa numarasi {i} kuantum ve yeterince uzun bir metin cumlesi"] for i in range(30)])
    indexer = TextIndexer(library, lambda: _InlinePool(), write_chunk=7)
    writes = []
    original = IndexService.add_pages

    def recording(self, document_id, first_page, texts):
        writes.append((first_page, len(texts)))
        return original(self, document_id, first_page, texts)

    monkeypatch.setattr(IndexService, "add_pages", recording)

    indexer.enqueue(many.id)
    _wait(indexer)

    assert writes == [(0, 7), (7, 7), (14, 7), (21, 7), (28, 2)]
    assert library.searching().search('"numarasi 29"')[0].page == 29


def test_cancel_stops_between_pages_and_leaves_no_partial_index(library, session, document):
    pool = _DeferredPool()
    indexer = TextIndexer(library, lambda: pool)

    indexer.enqueue(document.id)
    QTest.qWait(20)  # belge acildi, cikarim isi beklemede
    assert PageIndexRepository(session).state(document.id).status == STATUS_INDEXING
    indexer.cancel()
    pool.run_all()
    QTest.qWait(30)

    assert PageIndexRepository(session).state(document.id) is None and PageIndexRepository(session).page_row_count() == 0
    assert library.searching().search("kuantum") == [] and library.indexing().pending() == [document.id]
    assert indexer.status()["state"] == "idle"


def test_a_missing_file_fails_that_document_only(library, session, pdf_store, tmp_path, document):
    broken = _add(session, pdf_store, tmp_path, "kayip", [["kayip dosya hakkinda yeterince uzun bir metin var burada"]])
    pdf_store.absolute(broken.rel_path).unlink()
    indexer = TextIndexer(library, lambda: _InlinePool())

    indexer.scan()
    _wait(indexer)
    QTest.qWait(30)

    repo = PageIndexRepository(session)
    assert repo.state(broken.id).status == STATUS_FAILED and repo.state(document.id).status == STATUS_OK
    assert len(library.searching().search("kuantum")) == 2


def test_enqueue_ignores_duplicates_and_a_rescan_does_nothing_when_everything_is_indexed(library, document):
    indexer = TextIndexer(library, lambda: _InlinePool())

    indexer.enqueue(document.id)
    indexer.enqueue(document.id)
    _wait(indexer)
    indexer.scan()
    QTest.qWait(30)

    assert indexer.status()["total"] == 1 and indexer.status()["pending"] == 0


def test_results_are_grouped_by_resource_and_documents_without_a_resource_are_skipped(session, pdf_store, tmp_path, document):
    other = _add(session, pdf_store, tmp_path, "baska", [["kuantum baska belge ve yeterince uzun bir metin cumlesi"]])
    _index(session, document.id, [" ".join(p) for p in PAGES])
    _index(session, other.id, ["kuantum baska belge"])

    groups = SearchService(session).search_by_resource("kuantum")

    assert {g.document_id: (g.title, g.total) for g in groups} == {document.id: ("kuantum", 2), other.id: ("baska", 1)}
    assert all(g.resource_id for g in groups)
    session.execute(delete(PdfResourceLinkRow).where(PdfResourceLinkRow.document_id == other.id))
    session.commit()  # kaynagi silinmis belge (dizinde yetim kalmis): sonuclarda gorunmez
    assert [g.document_id for g in SearchService(session).search_by_resource("kuantum")] == [document.id]
