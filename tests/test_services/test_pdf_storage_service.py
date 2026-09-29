from models import Resource
from services.pdf_storage_service import PdfStorageService


def _resource(url=None, metadata=None):
    return Resource(title="t", url=url, extra_metadata=metadata)


def test_sweep_removes_only_unreferenced_pdfs(tmp_path):
    local_pdf = tmp_path / "local.pdf"
    downloaded_pdf = tmp_path / "web.pdf"
    orphan_pdf = tmp_path / "orphan.pdf"
    other_file = tmp_path / "notes.txt"
    for f in (local_pdf, downloaded_pdf, orphan_pdf, other_file):
        f.write_bytes(b"x")

    resources = [
        _resource(url=local_pdf.as_uri()),
        _resource(url="https://arxiv.org/pdf/1", metadata={"local_pdf": str(downloaded_pdf)}),
    ]

    removed = PdfStorageService(tmp_path).sweep_orphans(resources)

    assert removed == 1
    assert local_pdf.exists() and downloaded_pdf.exists() and other_file.exists()
    assert not orphan_pdf.exists()


def test_sweep_handles_missing_directory(tmp_path):
    assert PdfStorageService(tmp_path / "yok").sweep_orphans([]) == 0
