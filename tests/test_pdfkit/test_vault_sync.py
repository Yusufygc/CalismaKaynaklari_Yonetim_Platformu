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
    return sorted(p.name for p in papers.glob("[!_]*.md")) if papers.exists() else []  # "_" ile baslayanlar ozet notlari


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


# ---- ozet notlari: kutuphane dizini ve kelime defteri ----


def _summary(vault, name):
    path = vault / "Papers" / name
    return path.read_text(encoding="utf-8") if path.exists() else None


def test_full_sync_writes_the_library_index_and_skips_an_empty_vocabulary(sync, library, vault, doc):
    _resource, document = doc
    library.annotations().create_highlight(document.id, "alinti", [Segment(0, 0, 5, "alinti")], "method")
    reports = _reports(sync)
    sync.set_root(vault)

    sync.sync_all()

    index = _summary(vault, "_Index.md")
    assert "- [[lecun2015deep]] — Deep learning · Yann LeCun · 2015 · 1 alıntı · Gelen Kutusu" in index
    assert _summary(vault, "_Kelimeler.md") is None  # kelime yok: bos defter olusturulmaz
    assert reports[0].summaries_written == 1 and reports[0].created == 1
    assert "1 not yazıldı" in sync.status()["message"]  # ozet notlari belge sayisina karismaz


def test_terms_reach_the_vocabulary_note_and_counts_in_the_index_follow_changes(sync, library, vault, doc):
    resource, document = doc
    sync.set_root(vault)
    sync.sync_all()
    library.annotations().create_term(document.id, "ubiquitous", "her yerde", "It is ubiquitous.", [Segment(2, 0, 10, "ubiquitous")])
    reports = _reports(sync)

    sync.mark_resource(resource.id)
    QTest.qWait(120)

    vocabulary = _summary(vault, "_Kelimeler.md")
    assert "### [[lecun2015deep]] — Deep learning (1)" in vocabulary and "**ubiquitous** — her yerde" in vocabulary
    assert "1 kelime" in _summary(vault, "_Index.md")
    assert reports[0].summaries_written == 2


def test_unchanged_summaries_are_not_rewritten(sync, library, vault, doc):
    sync.set_root(vault)
    sync.sync_all()
    index = vault / "Papers" / "_Index.md"
    stamp = index.stat().st_mtime_ns
    reports = _reports(sync)

    sync.sync_all()

    assert reports[0].summaries_written == 0 and index.stat().st_mtime_ns == stamp


def test_summaries_wait_for_a_full_sync_so_a_partial_index_never_replaces_a_complete_one(sync, vault, doc):
    resource, _document = doc
    sync.set_root(vault)

    sync.mark_resource(resource.id)  # tam esitleme yok: onbellek eksik olabilir
    QTest.qWait(120)

    assert _notes(vault) == ["lecun2015deep.md"] and _summary(vault, "_Index.md") is None


def test_the_index_follows_new_documents_and_keeps_user_text(sync, library, vault, doc, session, pdf_store, tmp_path):
    sync.set_root(vault)
    sync.sync_all()
    index = vault / "Papers" / "_Index.md"
    index.write_text(index.read_text(encoding="utf-8") + "\nBenim notum.\n", encoding="utf-8")
    other, _other_document = _add_document(session, pdf_store, tmp_path, "iki")

    sync.mark_resource(other.id)
    QTest.qWait(120)

    text = index.read_text(encoding="utf-8")
    assert "Kaynaklar (2)" in text and "Benim notum." in text


def test_a_corrupted_summary_fails_alone_and_notes_are_still_written(sync, library, vault, doc):
    _resource, document = doc
    papers = vault / "Papers"
    papers.mkdir()
    (papers / "_Index.md").write_text("# Dizin\n%% pkm:end index %%\n", encoding="utf-8")
    library.annotations().create_highlight(document.id, "a", [Segment(0, 0, 1, "a")], "method")
    reports = _reports(sync)
    sync.set_root(vault)

    sync.sync_all()

    assert reports[0].failed[0][0] == "_Index.md" and reports[0].created == 1
    assert sync.status()["state"] == STATE_ERROR
    assert (papers / "_Index.md").read_text(encoding="utf-8") == "# Dizin\n%% pkm:end index %%\n"
