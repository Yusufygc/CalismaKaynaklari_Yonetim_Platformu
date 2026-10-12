from pathlib import Path

import pytest
from PySide6.QtTest import QTest

from models import Resource
from pdfkit.api import LegacyPdf, PdfLibrary
from pdfkit.infra.file_store import FileStore
from tests.pdf_factory import build_text_pdf, write_text_pdf
from tests.test_pdfkit.test_downloader import FakeStream


class SyncPool:
    def start(self, worker) -> None:
        worker.run()


class FakeCatalog:
    """Gercek oturumda Resource satiri olusturur; eski PDF listesini ve yonlendirmeleri kaydeder."""

    def __init__(self, session):
        self._session = session
        self.fail_create = False
        self.legacy: list[LegacyPdf] = []
        self.repointed: list[tuple[LegacyPdf, Path]] = []

    def create_pdf_resource(self, title, file_url, extra_metadata):
        if self.fail_create:
            return None
        resource = Resource(title=title, url=file_url, extra_metadata=extra_metadata)
        self._session.add(resource)
        self._session.commit()
        return resource.id

    def legacy_pdfs(self):
        return list(self.legacy)

    def repoint(self, legacy, new_path):
        self.repointed.append((legacy, new_path))
        return True


@pytest.fixture()
def catalog(session):
    return FakeCatalog(session)


@pytest.fixture()
def storage(tmp_path):
    return tmp_path / "pdfs"


def _library(session, storage, catalog, fetch=lambda url: None):
    return PdfLibrary(session, lambda: storage, catalog, lambda: SyncPool(), fetch)


@pytest.fixture()
def library(qapp, session, storage, catalog):
    return _library(session, storage, catalog)


def _capture(signal):
    received = []
    signal.connect(received.append)
    return received


def _pump(app, ms=60):
    QTest.qWait(ms)
    app.processEvents()


def test_import_local_creates_resource_document_and_reports_inspection(library, catalog, tmp_path):
    outcomes = _capture(library.importFinished)
    source = write_text_pdf(tmp_path / "Makale Adi.pdf")

    library.import_local(source)

    (outcome,) = outcomes
    assert outcome.status == "created" and outcome.resource_id is not None
    assert outcome.inspection.has_text_layer
    document = library.documents().document_for_resource(outcome.resource_id)
    assert document.sha256 == outcome.document.sha256 and document.source == "local"
    assert library.file_path(document).is_file()
    assert library.file_path(document).name == "Makale Adi.pdf"
    assert source.exists()


def test_importing_the_same_content_again_reports_duplicate_without_new_resource(library, session, tmp_path):
    outcomes = _capture(library.importFinished)
    library.import_local(write_text_pdf(tmp_path / "bir.pdf"))
    library.import_local(write_text_pdf(tmp_path / "iki.pdf"))  # ayni icerik, farkli ad

    first, second = outcomes
    assert first.status == "created" and second.status == "duplicate"
    assert second.resource_id == first.resource_id
    assert session.query(Resource).count() == 1


def test_import_of_a_non_pdf_is_invalid_and_creates_nothing(library, session, tmp_path):
    outcomes = _capture(library.importFinished)
    bad = tmp_path / "bozuk.pdf"
    bad.write_bytes(b"pdf degil")

    library.import_local(bad)

    assert [o.status for o in outcomes] == ["invalid"]
    assert session.query(Resource).count() == 0


def test_resource_creation_failure_quarantines_the_new_file(library, catalog, storage, tmp_path):
    outcomes = _capture(library.importFinished)
    catalog.fail_create = True

    library.import_local(write_text_pdf(tmp_path / "a.pdf"))

    assert [o.status for o in outcomes] == ["failed"]
    assert not list((storage / "store").rglob("*.pdf"))
    assert len(list((storage / ".trash").glob("*.pdf"))) == 1


def test_download_registers_document_and_reports_store_path(qapp, session, storage, catalog):
    body = build_text_pdf()
    library = _library(session, storage, catalog, fetch=lambda url: FakeStream([body]))
    resource_id = catalog.create_pdf_resource("Web", "https://arxiv.org/pdf/1706.03762", {})
    finished = []
    library.downloadFinished.connect(lambda rid, path: finished.append((rid, path)))

    library.download_remote(resource_id, "https://arxiv.org/pdf/1706.03762")

    ((rid, path),) = finished
    assert rid == resource_id and path.is_file() and path.name == "1706.03762.pdf"
    assert library.documents().document_for_resource(resource_id).source == "web"


def test_failed_download_reports_none(qapp, session, storage, catalog):
    library = _library(session, storage, catalog, fetch=lambda url: None)  # SSRF reddi
    finished = []
    library.downloadFinished.connect(lambda rid, path: finished.append((rid, path)))

    library.download_remote(7, "http://internal/x.pdf")

    assert finished == [(7, None)]


def _legacy_setup(session, storage, catalog, tmp_path, name="ab12cd34_Eski Makale.pdf"):
    storage.mkdir(parents=True, exist_ok=True)
    legacy_file = write_text_pdf(storage / name)
    resource = Resource(title="Eski", url=legacy_file.as_uri())
    session.add(resource)
    session.commit()
    catalog.legacy = [LegacyPdf(resource.id, legacy_file, "url")]
    return resource, legacy_file


def test_adopt_legacy_moves_old_pdfs_into_the_store_and_repoints_resources(
    qapp, library, session, storage, catalog, tmp_path
):
    resource, legacy_file = _legacy_setup(session, storage, catalog, tmp_path)
    done = _capture(library.legacyAdoptionFinished)

    library.adopt_legacy()
    _pump(qapp)

    assert done == [1]
    ((item, new_path),) = catalog.repointed
    assert item.resource_id == resource.id
    assert new_path.is_file() and new_path.name == "Eski Makale.pdf"  # uuid oneki atildi
    assert library.documents().document_for_resource(resource.id) is not None
    assert legacy_file.exists()  # eski dosya silinmez; sweep_orphans sonraki acilista karantinaya alir


def test_adopt_legacy_is_idempotent_and_skips_missing_files(qapp, library, session, storage, catalog, tmp_path):
    resource, legacy_file = _legacy_setup(session, storage, catalog, tmp_path)
    ghost = Resource(title="Kayip", url=(storage / "yok.pdf").as_uri())
    session.add(ghost)
    session.commit()
    catalog.legacy.append(LegacyPdf(ghost.id, storage / "yok.pdf", "url"))
    done = _capture(library.legacyAdoptionFinished)

    library.adopt_legacy()
    _pump(qapp)
    library.adopt_legacy()
    _pump(qapp)

    assert done[0] == 1  # kayip dosya atlandi
    assert len(catalog.repointed) == 1  # ikinci cagri: bagli kaynak yeniden islenmedi, kayip olan yine atlandi
    assert library.documents().document_for_resource(ghost.id) is None


def test_two_legacy_resources_with_identical_pdf_share_one_document(qapp, library, session, storage, catalog, tmp_path):
    first, file_a = _legacy_setup(session, storage, catalog, tmp_path, "11111111_a.pdf")
    second_file = write_text_pdf(storage / "22222222_b.pdf")  # ayni icerik
    second = Resource(title="Kopya", url=second_file.as_uri())
    session.add(second)
    session.commit()
    catalog.legacy.append(LegacyPdf(second.id, second_file, "url"))

    library.adopt_legacy()
    _pump(qapp)

    documents = library.documents()
    assert documents.document_for_resource(first.id).id == documents.document_for_resource(second.id).id
    assert len(list((storage / "store").rglob("*.pdf"))) == 1


def test_garbage_collection_retries_until_a_locked_file_can_be_moved(qapp, library, session, storage, catalog, tmp_path, monkeypatch):
    outcomes = _capture(library.importFinished)
    library.import_local(write_text_pdf(tmp_path / "a.pdf"))
    resource = session.get(Resource, outcomes[0].resource_id)
    session.delete(resource)
    session.commit()

    real = FileStore.quarantine
    calls = {"n": 0}

    def flaky(self, rel_path):
        calls["n"] += 1
        return False if calls["n"] == 1 else real(self, rel_path)  # ilk deneme: Windows kilidi

    monkeypatch.setattr(FileStore, "quarantine", flaky)

    library.collect_garbage(attempts=3, interval_ms=10)
    assert list((storage / "store").rglob("*.pdf"))  # kilitli: henuz tasinamadi
    _pump(qapp, 120)

    assert not list((storage / "store").rglob("*.pdf"))
    assert calls["n"] >= 2


def test_maintenance_copies_legacy_annotations_once_adoption_has_finished(qapp, library, session, tmp_path):
    from models import Highlight

    outcomes = _capture(library.importFinished)
    library.import_local(write_text_pdf(tmp_path / "a.pdf"))
    resource_id = outcomes[0].resource_id
    session.add(Highlight(resource_id=resource_id, content="Hizli kahverengi", color="#22C55E", page_number=0, start_index=0, length=16))
    session.commit()

    library.start_maintenance()  # bos benimseme -> kopyalama

    document = library.documents().document_for_resource(resource_id)
    (copied,) = library.annotations().list_highlights(document.id)
    assert copied.quote_exact == "Hizli kahverengi" and copied.legacy_id is not None


def test_documents_are_found_by_sha_prefix_only_when_unambiguous(pdf_library, session, pdf_store, tmp_path):
    from models import Resource
    from pdfkit.app.documents import DocumentService
    from pdfkit.app.importing import prepare_pdf
    from tests.pdf_factory import write_outline_pdf

    documents = []
    for name in ("a", "b"):
        prepared = prepare_pdf(write_outline_pdf(tmp_path / f"{name}.pdf", [name.upper()]), pdf_store)
        resource = Resource(title=name, url=pdf_store.absolute(prepared.stored.rel_path).as_uri())
        session.add(resource)
        session.commit()
        documents.append(DocumentService(session, pdf_store).register(prepared, resource.id, "local"))
    service = pdf_library.documents()
    first, second = documents

    assert service.find_by_sha_prefix(first.sha256[:16]) == first
    assert service.find_by_sha_prefix(first.sha256) == first
    assert service.find_by_sha_prefix("0" * 16) is None
    shared = ""
    for left, right in zip(first.sha256, second.sha256):
        if left != right:
            break
        shared += left
    if shared:  # ortak onek varsa belirsiz sayilir
        assert service.find_by_sha_prefix(shared) is None
    assert service.find_by_sha_prefix("%") is None and service.find_by_sha_prefix("_") is None  # LIKE jokerleri kacirilir
