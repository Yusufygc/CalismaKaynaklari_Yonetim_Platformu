import pytest

from models import Resource
from pdfkit.app.documents import DocumentService
from pdfkit.app.importing import prepare_pdf, prepare_remote_pdf
from pdfkit.domain.errors import NotAPdfError
from pdfkit.infra.file_store import FileStore
from tests.pdf_factory import build_text_pdf, write_text_pdf
from tests.test_pdfkit.test_downloader import FakeStream


@pytest.fixture()
def store(tmp_path):
    return FileStore(tmp_path / "pdfs")


@pytest.fixture()
def service(session, store):
    return DocumentService(session, store)


def _resource(session, title="R"):
    resource = Resource(title=title)
    session.add(resource)
    session.commit()
    return resource


def test_prepare_pdf_hashes_stores_and_does_not_touch_source(tmp_path, store):
    source = write_text_pdf(tmp_path / "a.pdf")

    prepared = prepare_pdf(source, store)

    assert store.exists(prepared.stored.rel_path)
    assert prepared.stored.created
    assert prepared.inspection.has_text_layer
    assert prepared.original_filename == "a.pdf"
    assert source.exists()


def test_same_content_under_different_names_is_one_stored_file(tmp_path, store):
    first = prepare_pdf(write_text_pdf(tmp_path / "bir.pdf"), store)
    second = prepare_pdf(write_text_pdf(tmp_path / "iki.pdf"), store)

    assert first.stored.sha256 == second.stored.sha256
    assert not second.stored.created


def test_prepare_pdf_rejects_garbage_without_copying(tmp_path, store):
    bad = tmp_path / "bozuk.pdf"
    bad.write_bytes(b"degil")

    with pytest.raises(NotAPdfError):
        prepare_pdf(bad, store)

    assert not list((store.root).rglob("*.pdf"))


def test_register_creates_document_and_link_and_is_idempotent(tmp_path, store, service, session):
    prepared = prepare_pdf(write_text_pdf(tmp_path / "a.pdf"), store)
    resource = _resource(session)

    document = service.register(prepared, resource.id, "local")
    again = service.register(prepared, resource.id, "local")

    assert document.id == again.id
    assert service.document_for_resource(resource.id).sha256 == prepared.stored.sha256
    assert service.resources_with_document(document.id) == [resource.id]


def test_two_resources_can_share_one_document(tmp_path, store, service, session):
    prepared = prepare_pdf(write_text_pdf(tmp_path / "a.pdf"), store)
    first, second = _resource(session, "A"), _resource(session, "B")

    doc_a = service.register(prepared, first.id, "web")
    doc_b = service.register(prepared, second.id, "web")

    assert doc_a.id == doc_b.id
    assert sorted(service.resources_with_document(doc_a.id)) == sorted([first.id, second.id])


def test_gc_keeps_shared_document_until_last_resource_is_gone(tmp_path, store, service, session):
    prepared = prepare_pdf(write_text_pdf(tmp_path / "a.pdf"), store)
    first, second = _resource(session, "A"), _resource(session, "B")
    service.register(prepared, first.id, "web")
    service.register(prepared, second.id, "web")

    session.delete(first)
    session.commit()
    assert service.collect_garbage().collected == 0
    assert store.exists(prepared.stored.rel_path)

    session.delete(second)
    session.commit()
    assert service.collect_garbage().collected == 1
    assert not store.exists(prepared.stored.rel_path)
    assert len(list((store.root / ".trash").glob("*.pdf"))) == 1
    assert service.find_by_sha(prepared.stored.sha256) is None


def test_prepare_remote_pdf_streams_into_store_and_cleans_temp(store):
    body = build_text_pdf()
    stream = FakeStream([body[:100], body[100:]])

    prepared = prepare_remote_pdf(
        "https://arxiv.org/pdf/1706.03762", store, fetch=lambda url: stream, max_bytes=10_000_000
    )

    assert store.exists(prepared.stored.rel_path)
    assert prepared.original_filename == "1706.03762"
    assert prepared.stored.rel_path.endswith("/1706.03762.pdf")
    assert not list(store.temp_dir.iterdir())


def test_gc_quarantines_old_stray_store_files_but_spares_fresh_and_registered(tmp_path, store, service, session):
    import os
    import time

    registered = prepare_pdf(write_text_pdf(tmp_path / "kayitli.pdf"), store)
    service.register(registered, _resource(session).id, "local")
    stray = prepare_pdf(write_text_pdf(tmp_path / "sahipsiz.pdf", ["baska icerik burada"]), store)  # satiri yok
    fresh = prepare_pdf(write_text_pdf(tmp_path / "taze.pdf", ["yeni yazilan dosya"]), store)

    old = time.time() - 2 * 3600
    os.utime(store.absolute(stray.stored.rel_path), (old, old))

    assert service.collect_garbage().collected == 1
    assert store.exists(registered.stored.rel_path)
    assert store.exists(fresh.stored.rel_path)  # henuz kaydi eklenmemis olabilir
    assert not store.exists(stray.stored.rel_path)
