import os
import time

from pdfkit.infra.file_store import TRASH_DIR_NAME, FileStore, safe_pdf_name

SHA = "ab" + "0" * 62


def test_safe_pdf_name_is_windows_safe_short_and_always_pdf():
    assert safe_pdf_name("Attention: Is/All?.PDF") == "Attention_ Is_All_.pdf"
    assert safe_pdf_name("") == "belge.pdf"
    assert safe_pdf_name(None) == "belge.pdf"
    assert safe_pdf_name("...") == "belge.pdf"
    assert len(safe_pdf_name("a" * 200)) == 64


def test_ingest_copies_atomically_and_leaves_source(tmp_path):
    source = tmp_path / "kaynak.pdf"
    source.write_bytes(b"%PDF-1.4 icerik")
    store = FileStore(tmp_path / "pdfs")

    stored = store.ingest(source, SHA)

    assert stored.created and stored.byte_size == len(b"%PDF-1.4 icerik")
    assert stored.rel_path == f"store/ab/{SHA}/kaynak.pdf"  # dizin = icerik ozeti, dosya = okunur ad
    assert store.absolute(stored.rel_path).read_bytes() == b"%PDF-1.4 icerik"
    assert source.exists()
    assert not list((tmp_path / "pdfs").rglob("*.part"))


def test_ingest_same_content_does_not_copy_again(tmp_path):
    source = tmp_path / "a.pdf"
    source.write_bytes(b"%PDF-1.4 x")
    store = FileStore(tmp_path / "pdfs")
    store.ingest(source, SHA)

    other_name = tmp_path / "baska-ad.pdf"
    other_name.write_bytes(b"%PDF-1.4 x")
    again = store.ingest(other_name, SHA)

    assert not again.created
    assert again.rel_path == f"store/ab/{SHA}/a.pdf"  # ilk gorulen ad korunur
    assert store.find(SHA) == again.rel_path


def test_ingest_rewrites_truncated_file(tmp_path):
    source = tmp_path / "a.pdf"
    source.write_bytes(b"%PDF-1.4 tam icerik")
    store = FileStore(tmp_path / "pdfs")
    first = store.ingest(source, SHA)
    store.absolute(first.rel_path).write_bytes(b"kesik")

    again = store.ingest(source, SHA)

    assert again.created
    assert store.absolute(again.rel_path).read_bytes() == b"%PDF-1.4 tam icerik"


def test_quarantine_moves_instead_of_deleting_and_missing_file_is_ok(tmp_path):
    source = tmp_path / "a.pdf"
    source.write_bytes(b"%PDF-1.4 x")
    store = FileStore(tmp_path / "pdfs")
    stored = store.ingest(source, SHA)

    assert store.quarantine(stored.rel_path)

    assert not store.exists(stored.rel_path)
    assert len(list((tmp_path / "pdfs" / TRASH_DIR_NAME).glob("*.pdf"))) == 1
    assert store.find(SHA) is None
    assert not (tmp_path / "pdfs" / "store" / "ab").exists()  # bos dizinler temizlenir
    assert store.quarantine(stored.rel_path)  # zaten yok -> sorun degil


def test_purge_trash_removes_only_expired(tmp_path):
    store = FileStore(tmp_path)
    trash = tmp_path / TRASH_DIR_NAME
    trash.mkdir()
    fresh, expired = trash / "taze.pdf", trash / "eski.pdf"
    fresh.write_bytes(b"x")
    expired.write_bytes(b"x")
    old = time.time() - 31 * 86400
    os.utime(expired, (old, old))

    assert store.purge_trash(retention_days=30) == 1
    assert fresh.exists() and not expired.exists()
