import pytest

from ui_qml.pdf_files import PdfFileManager


@pytest.fixture(autouse=True)
def _no_real_pdf_downloads(monkeypatch):
    """Web-PDF'i acan testler gercek ag istegi atmasin (indirme bridge testlerinde
    ayrica, sahte worker ile test ediliyor)."""
    monkeypatch.setattr(PdfFileManager, "start_download", lambda self, resource: None)
