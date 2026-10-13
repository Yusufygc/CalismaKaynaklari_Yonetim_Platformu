"""Arama ayri bir okuma oturumuyla havuz thread'inde calisir (dosya veritabani); bellek ici veritabaninda ana oturumda."""
import threading

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from models import Resource
from models.base import Base
from pdfkit.api import PdfLibrary
from pdfkit.app.documents import DocumentService
from pdfkit.app.importing import prepare_pdf
from pdfkit.app.search import IndexService
from tests.pdf_factory import write_multipage_text_pdf
from tests.test_pdfkit.conftest import NullCatalog
from ui_qml.context import read_session_factory
from utils import db_utils


class ThreadPerJobPool:
    """Her isi gercek bir thread'de calistirir; `drain` hepsini bekler (sinyaller ana thread'e kuyruklanir)."""

    def __init__(self):
        self.threads = []
        self.worker_threads = []

    def start(self, worker):
        def run():
            self.worker_threads.append(threading.current_thread())
            worker.run()

        thread = threading.Thread(target=run)
        self.threads.append(thread)
        thread.start()

    def drain(self, app):
        for thread in self.threads:
            thread.join(timeout=5)
        app.processEvents()


@pytest.fixture()
def file_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _configure(dbapi_connection, _record) -> None:
        db_utils.configure_sqlite_connection(dbapi_connection, True)

    db_utils.register_sqlite_functions(engine)
    import pdfkit.infra.orm  # noqa: F401

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _indexed_library(qapp, session, pdf_store, tmp_path, pool):
    prepared = prepare_pdf(write_multipage_text_pdf(tmp_path / "kuantum.pdf", [["Kuantum bilgisayarlar hakkinda giris bolumu ve baska seyler."]]), pdf_store)
    resource = Resource(title="kuantum", url=pdf_store.absolute(prepared.stored.rel_path).as_uri())
    session.add(resource)
    session.commit()
    document = DocumentService(session, pdf_store).register(prepared, resource.id, "local")
    service = IndexService(session)
    assert service.available()
    service.begin(document.id)
    service.add_pages(document.id, 0, ["Kuantum bilgisayarlar hakkinda giris bolumu ve baska seyler."])
    service.finish(document.id, 1)
    return PdfLibrary(session, lambda: pdf_store.root, NullCatalog(), lambda: pool, lambda url: None, read_session=read_session_factory(session)), resource


def test_the_factory_exists_only_for_file_databases(session, file_session):
    assert read_session_factory(session) is None  # bellek ici: her baglanti ayri bos veritabani
    assert read_session_factory(file_session) is not None


def test_search_runs_on_a_pool_thread_with_its_own_session_and_returns_to_the_caller(qapp, file_session, pdf_store, tmp_path):
    pool = ThreadPerJobPool()
    library, resource = _indexed_library(qapp, file_session, pdf_store, tmp_path, pool)
    results = []

    library.search_async("kuantum", lambda groups, error: results.append((groups, error, threading.current_thread())))
    assert results == []  # henuz donmedi: ana thread bloklanmadi
    pool.drain(qapp)

    (groups, error, caller), = results
    assert error is None and [g.resource_id for g in groups] == [resource.id]
    assert caller is threading.main_thread() and pool.worker_threads and pool.worker_threads[0] is not threading.main_thread()


def test_a_search_while_the_main_session_holds_an_open_write_is_not_blocked(qapp, file_session, pdf_store, tmp_path):
    from sqlalchemy import text

    pool = ThreadPerJobPool()
    library, _resource = _indexed_library(qapp, file_session, pdf_store, tmp_path, pool)
    file_session.execute(text("UPDATE resources SET title = 'degisti'"))  # commit edilmemis yazma (WAL: okuyucu beklemez)
    results = []

    library.search_async("kuantum", lambda groups, error: results.append((groups, error)))
    pool.drain(qapp)
    file_session.rollback()

    assert results and results[0][1] is None and len(results[0][0]) == 1


def test_without_a_read_session_the_search_runs_inline_on_the_main_session(session, pdf_store, qapp):
    library = PdfLibrary(session, lambda: pdf_store.root, NullCatalog(), lambda: None, lambda url: None)
    results = []

    library.search_async("kuantum", lambda groups, error: results.append((groups, error)))

    assert results == [([], None)]  # esdeger: dizin yok -> bos, hata yok, hemen
