"""VaultSync: degisen belgelerin notlarini arka planda, birlestirilmis olarak vault'a yazar."""
import pytest
from PySide6.QtTest import QTest

from models import Resource
from pdfkit.api import PdfLibrary, SourceInfo, VaultSync, VaultUnavailableError
from pdfkit.app.documents import DocumentService
from pdfkit.app.importing import prepare_pdf
from pdfkit.domain.annotations import Segment
from pdfkit.ui.vault import STATE_DISABLED, STATE_ERROR, STATE_IDLE, STATE_PENDING
from tests.pdf_factory import write_outline_pdf
from tests.test_pdfkit.conftest import NullCatalog


class InfoCatalog(NullCatalog):
    def describe(self, resource_id):
        return SourceInfo("Deep learning", ("Yann LeCun",), 2015, "10.1038/nature14539", "Gelen Kutusu")


class _InlinePool:
    def start(self, worker):
        worker.run()


@pytest.fixture()
def library(qapp, session, pdf_store):
    return PdfLibrary(session, lambda: pdf_store.root, InfoCatalog(), lambda: _InlinePool(), lambda url: None)


@pytest.fixture()
def vault(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    return root


@pytest.fixture()
def sync(library):
    return VaultSync(library, lambda: _InlinePool(), debounce_ms=20)


def _add_document(session, pdf_store, tmp_path, name):
    prepared = prepare_pdf(write_outline_pdf(tmp_path / f"{name}.pdf", [name.upper(), "B"]), pdf_store)
    resource = Resource(title=name, url=pdf_store.absolute(prepared.stored.rel_path).as_uri())
    session.add(resource)
    session.commit()
    return resource, DocumentService(session, pdf_store).register(prepared, resource.id, "local")


@pytest.fixture()
def doc(session, pdf_store, tmp_path):
    return _add_document(session, pdf_store, tmp_path, "bir")


def _reports(sync):
    reports = []
    sync.syncFinished.connect(reports.append)
    return reports


def _notes(vault):
    papers = vault / "Papers"
    return sorted(p.name for p in papers.glob("*.md")) if papers.exists() else []


def test_nothing_happens_while_no_vault_is_configured(sync, doc):
    resource, _document = doc
    reports = _reports(sync)

    sync.mark_resource(resource.id)
    sync.sync_all()
    QTest.qWait(80)

    assert reports == [] and sync.status()["state"] == STATE_DISABLED and not sync.status()["enabled"]


def test_sync_all_writes_a_note_per_pdf_document_with_a_stable_citekey(sync, library, vault, doc, session):
    resource, document = doc
    library.annotations().create_highlight(document.id, "ilk alinti", [Segment(0, 0, 10, "ilk alinti")], "finding")
    reports = _reports(sync)
    sync.set_root(vault)

    sync.sync_all()

    assert _notes(vault) == ["lecun2015deep.md"] and reports[0].created == 1 and reports[0].failed == []
    text = (vault / "Papers" / "lecun2015deep.md").read_text(encoding="utf-8")
    assert "ilk alinti" in text and 'status: "Gelen Kutusu"' in text
    assert sync.status()["state"] == STATE_IDLE and "1 not yazıldı" in sync.status()["message"] and sync.status()["lastSync"]


def test_a_second_full_sync_changes_nothing(sync, library, vault, doc):
    _resource, document = doc
    library.annotations().create_highlight(document.id, "alinti", [Segment(0, 0, 5, "alinti")], "method")
    reports = _reports(sync)
    sync.set_root(vault)
    sync.sync_all()
    note = vault / "Papers" / "lecun2015deep.md"
    first_mtime = note.stat().st_mtime_ns

    sync.sync_all()

    assert (reports[1].created, reports[1].updated, reports[1].unchanged) == (0, 0, 1)
    assert note.stat().st_mtime_ns == first_mtime


def test_many_marks_in_a_burst_are_merged_into_one_sync_after_the_debounce(sync, library, vault, doc):
    resource, document = doc
    reports = _reports(sync)
    sync.set_root(vault)

    for _ in range(5):
        sync.mark_resource(resource.id)
    assert sync.status()["state"] == STATE_PENDING and reports == []  # henuz yazilmadi: UI yolunu bloklamaz
    QTest.qWait(120)

    assert len(reports) == 1 and reports[0].created == 1


def test_marking_a_resource_without_a_pdf_document_is_ignored(sync, session, vault):
    web = Resource(title="Web", url="https://x.org/a")
    session.add(web)
    session.commit()
    reports = _reports(sync)
    sync.set_root(vault)

    sync.mark_resource(web.id)
    QTest.qWait(80)

    assert reports == [] and _notes(vault) == []


def test_a_new_annotation_updates_the_note_and_keeps_user_text(sync, library, vault, doc):
    resource, document = doc
    sync.set_root(vault)
    sync.sync_all()
    note = vault / "Papers" / "lecun2015deep.md"
    note.write_text(note.read_text(encoding="utf-8") + "\nBenim satirim.\n", encoding="utf-8")
    library.annotations().create_highlight(document.id, "sonradan eklenen", [Segment(0, 0, 9, "x")], "concept")
    reports = _reports(sync)

    sync.mark_resource(resource.id)
    QTest.qWait(120)

    text = note.read_text(encoding="utf-8")
    assert reports[0].updated == 1 and "sonradan eklenen" in text and "Benim satirim." in text


def test_a_corrupted_note_fails_alone_while_other_notes_are_still_written(sync, library, vault, doc, session, pdf_store, tmp_path):
    bad_resource, bad_document = doc
    other_resource, other_document = _add_document(session, pdf_store, tmp_path, "iki")
    sync.set_root(vault)
    sync.sync_all()
    names = _notes(vault)
    assert len(names) == 2
    broken = vault / "Papers" / names[0]
    broken.write_text(broken.read_text(encoding="utf-8").replace("%% pkm:end annotations %%", ""), encoding="utf-8")
    library.annotations().create_highlight(bad_document.id, "a", [Segment(0, 0, 1, "a")], "method")
    library.annotations().create_highlight(other_document.id, "b", [Segment(0, 0, 1, "b")], "method")
    reports = _reports(sync)

    sync.sync_all()

    assert len(reports[0].failed) == 1 and reports[0].updated == 1
    assert sync.status()["state"] == STATE_ERROR and "1 not yazılamadı" in sync.status()["message"]
    assert "pkm:end" not in broken.read_text(encoding="utf-8")  # bozuk dosyaya dokunulmadi


def test_mark_during_a_running_sync_is_not_lost(sync, library, vault, doc, monkeypatch):
    resource, document = doc
    reports = _reports(sync)
    sync.set_root(vault)
    original = sync._on_written

    def mark_then_finish(report, error):
        if not getattr(mark_then_finish, "done", False):
            mark_then_finish.done = True
            library.annotations().create_highlight(document.id, "gec", [Segment(0, 0, 3, "gec")], "method")
            sync.mark_resource(resource.id)  # esitleme sirasinda yeni degisiklik
        original(report, error)

    monkeypatch.setattr(sync, "_on_written", mark_then_finish)
    # _on_written baglantisi `CallWorker` olusturulurken okunur: yeni isaretleme tekrar planlanmali
    sync.sync_all()
    QTest.qWait(150)

    assert "gec" in (vault / "Papers" / "lecun2015deep.md").read_text(encoding="utf-8")
    assert len(reports) == 2


def test_set_root_rejects_unusable_folders_and_keeps_the_previous_setting(sync, vault, tmp_path):
    sync.set_root(vault)

    with pytest.raises(VaultUnavailableError):
        sync.set_root(tmp_path / "yok")

    assert sync.root == vault and sync.status()["enabled"]


def test_clearing_the_root_disables_syncing_but_keeps_existing_notes(sync, vault, doc):
    sync.set_root(vault)
    sync.sync_all()

    sync.set_root(None)
    sync.sync_all()

    assert sync.status()["state"] == STATE_DISABLED and _notes(vault) == ["lecun2015deep.md"]  # silinmez
