from models import Resource
import os
import time

from services.pdf_storage_service import TRASH_DIR_NAME, TRASH_RETENTION_DAYS, PdfStorageService


def _resource(url=None, metadata=None):
    return Resource(title="t", url=url, extra_metadata=metadata)


def test_sweep_quarantines_only_unreferenced_pdfs(tmp_path):
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
    assert (tmp_path / TRASH_DIR_NAME / "orphan.pdf").read_bytes() == b"x"  # silinmedi, geri alinabilir


def test_sweep_handles_missing_directory(tmp_path):
    assert PdfStorageService(tmp_path / "yok").sweep_orphans([]) == 0


def test_sweep_never_touches_files_when_library_is_empty(tmp_path):
    """Bos/yeni/sifirlanmis veritabani: tum PDF'ler yetim gorunur ama hicbiri tasinmamali."""
    pdf = tmp_path / "kitap.pdf"
    pdf.write_bytes(b"x")

    assert PdfStorageService(tmp_path).sweep_orphans([]) == 0

    assert pdf.exists()
    assert not (tmp_path / TRASH_DIR_NAME).exists()


def test_sweep_purges_only_expired_trash(tmp_path):
    trash = tmp_path / TRASH_DIR_NAME
    trash.mkdir()
    fresh, expired = trash / "taze.pdf", trash / "eski.pdf"
    fresh.write_bytes(b"x")
    expired.write_bytes(b"x")
    old = time.time() - (TRASH_RETENTION_DAYS + 1) * 86400
    os.utime(expired, (old, old))

    PdfStorageService(tmp_path).sweep_orphans([_resource(url="https://example.com/a")])

    assert fresh.exists()
    assert not expired.exists()
