"""SynthesisService: veritabanindan literatur matrisi satirlari (toplu okuma, kunye, citekey, suzgec)."""
import pytest
from sqlalchemy import delete

from models import Resource
from pdfkit.api import MatrixFilter, PdfLibrary, SourceInfo
from pdfkit.app.documents import DocumentService
from pdfkit.app.importing import prepare_pdf
from pdfkit.app.vault import CitekeyService
from pdfkit.domain.annotations import Segment
from pdfkit.infra.orm import PdfResourceLinkRow
from tests.pdf_factory import write_multipage_text_pdf
from tests.test_pdfkit.conftest import NullCatalog


class InfoCatalog(NullCatalog):
    def describe(self, resource_id):
        return SourceInfo(f"Kaynak {resource_id}", ("Yazar",), 2000 + resource_id)


class _Pool:
    def start(self, worker):
        worker.run()


def _add(session, pdf_store, tmp_path, name):
    prepared = prepare_pdf(write_multipage_text_pdf(tmp_path / f"{name}.pdf", [[f"{name} sayfa metni yeterince uzun bir cumle olsun"]]), pdf_store)
    resource = Resource(title=name, url=pdf_store.absolute(prepared.stored.rel_path).as_uri())
    session.add(resource)
    session.commit()
    return resource, DocumentService(session, pdf_store).register(prepared, resource.id, "local")


@pytest.fixture()
def library(qapp, session, pdf_store):
    return PdfLibrary(session, lambda: pdf_store.root, InfoCatalog(), lambda: _Pool(), lambda url: None)


def _highlight(library, document, text, label, page=0, tags=None):
    return library.annotations().create_highlight(
        document.id, text, [Segment(page, 0, len(text), text)], label, tags=tags
    )


def test_rows_group_each_documents_annotations_with_source_info(library, session, pdf_store, tmp_path):
    first_resource, first = _add(session, pdf_store, tmp_path, "bir")
    second_resource, second = _add(session, pdf_store, tmp_path, "iki")
    _highlight(library, first, "yontem bir", "method", page=2)
    _highlight(library, first, "bulgu bir", "finding")
    _highlight(library, second, "yontem iki", "method")

    rows = {row.document.id: row for row in library.synthesis().rows()}

    row = rows[first.id]
    assert (row.title, row.year, row.resource_id) == (f"Kaynak {first_resource.id}", 2000 + first_resource.id, first_resource.id)
    assert {key: len(items) for key, items in row.cells.items()} == {"method": 1, "finding": 1}
    assert set(rows) == {first.id, second.id}


def test_citekeys_are_included_when_assigned_and_never_created_by_reading(library, session, pdf_store, tmp_path):
    _resource, document = _add(session, pdf_store, tmp_path, "bir")
    _highlight(library, document, "yontem", "method")
    assert library.synthesis().rows()[0].citekey is None  # okumak citekey atamaz (yazma yan etkisi yok)

    CitekeyService(session).ensure(document, SourceInfo("Kuantum", ("Ada Yazar",), 2020))

    assert library.synthesis().rows()[0].citekey == "yazar2020kuantum"


def test_documents_without_annotations_or_without_a_resource_are_not_rows(library, session, pdf_store, tmp_path):
    _add(session, pdf_store, tmp_path, "bos")  # alintisi yok
    _resource, orphaned = _add(session, pdf_store, tmp_path, "kaynaksiz")
    _highlight(library, orphaned, "yontem", "method")
    session.execute(delete(PdfResourceLinkRow).where(PdfResourceLinkRow.document_id == orphaned.id))
    session.commit()

    assert library.synthesis().rows() == []


def test_a_document_shared_by_two_resources_is_one_row_owned_by_the_smallest_resource_id(library, session, pdf_store, tmp_path):
    resource, document = _add(session, pdf_store, tmp_path, "ortak")
    _highlight(library, document, "yontem", "method")
    second = Resource(title="ikinci kayit", url=resource.url)
    session.add(second)
    session.commit()
    session.add(PdfResourceLinkRow(resource_id=second.id, document_id=document.id))
    session.commit()

    (row,) = library.synthesis().rows()

    assert row.resource_id == min(resource.id, second.id)


def test_matrix_applies_the_filter(library, session, pdf_store, tmp_path):
    _r1, first = _add(session, pdf_store, tmp_path, "bir")
    _r2, second = _add(session, pdf_store, tmp_path, "iki")
    _highlight(library, first, "yontem bir", "method", tags=["hipotez"])
    _highlight(library, second, "bulgu iki", "finding")

    by_label = library.synthesis().matrix(MatrixFilter(labels=("finding",)))
    by_tag = library.synthesis().matrix(MatrixFilter(tag="hipotez"))

    assert [row.document.id for row in by_label.rows] == [second.id]
    assert [row.document.id for row in by_tag.rows] == [first.id]


def test_rows_for_reads_only_the_given_documents(library, session, pdf_store, tmp_path):
    _r1, first = _add(session, pdf_store, tmp_path, "bir")
    _r2, second = _add(session, pdf_store, tmp_path, "iki")
    _highlight(library, first, "yontem bir", "method")
    _highlight(library, second, "yontem iki", "method")

    only_second = library.synthesis().rows_for([second.id])

    assert [row.document.id for row in only_second] == [second.id]
    assert library.synthesis().rows_for([]) == []  # bos liste tum kutuphaneyi OKUMAZ
    assert library.synthesis().rows_for([999]) == []  # alintisi/belgesi olmayan: satir yok


def test_source_info_is_fetched_in_one_call_for_all_rows_instead_of_one_per_document(session, pdf_store, tmp_path, qapp):
    calls = []

    class CountingCatalog(InfoCatalog):
        def describe(self, resource_id):
            calls.append(("one", resource_id))
            return super().describe(resource_id)

        def describe_many(self, resource_ids):
            calls.append(("many", tuple(resource_ids)))
            return {resource_id: InfoCatalog.describe(self, resource_id) for resource_id in resource_ids}

    library = PdfLibrary(session, lambda: pdf_store.root, CountingCatalog(), lambda: _Pool(), lambda url: None)
    for name in ("bir", "iki", "uc"):
        _resource, document = _add(session, pdf_store, tmp_path, name)
        _highlight(library, document, f"yontem {name}", "method")

    rows = library.synthesis().rows()

    assert len(rows) == 3 and [kind for kind, _ in calls] == ["many"]  # N+1 yok
