import pytest

from models import Resource
from pdfkit.app.annotations import AnnotationService
from pdfkit.app.documents import DocumentService
from pdfkit.app.importing import prepare_pdf
from pdfkit.infra.file_store import FileStore
from tests.pdf_factory import write_text_pdf

SENTENCE = "Hizli kahverengi tilki tembel kopegin ustunden atlar."
LINES = [f"Birinci cumle burada biter. {SENTENCE} Ucuncu cumle.", "Ikinci satir baska bir paragrafin baslangicidir."]


@pytest.fixture()
def pdf_store(tmp_path):
    return FileStore(tmp_path / "pdfs")


@pytest.fixture()
def resource_with_document(session, pdf_store, tmp_path):
    """(resource, document, pdf_yolu): gercek bir PDF'e bagli kaynak ve belge."""
    source = write_text_pdf(tmp_path / "makale.pdf", LINES)
    prepared = prepare_pdf(source, pdf_store)
    resource = Resource(title="Makale", url=pdf_store.absolute(prepared.stored.rel_path).as_uri())
    session.add(resource)
    session.commit()
    document = DocumentService(session, pdf_store).register(prepared, resource.id, "local")
    return resource, document, pdf_store.absolute(prepared.stored.rel_path)


@pytest.fixture()
def annotations(session):
    return AnnotationService(session)
