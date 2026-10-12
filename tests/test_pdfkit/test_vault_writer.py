"""VaultWriter: atomik yazim, degismediyse yazmama, kullanici duzenlemesini ezmeme, yol ve dosya guvenligi."""
import os
import time

import pytest

from pdfkit.domain.errors import VaultConflictError, VaultNoteError, VaultUnavailableError
from pdfkit.domain.vault_note import NoteContent, compose_note
from pdfkit.infra import vault_writer as vault_writer_module
from pdfkit.infra.vault_writer import VaultWriter, WriteOutcome
from tests.test_pdfkit.vault_samples import DOCUMENT, INFO, annotation, sample_content


@pytest.fixture()
def vault(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    return root


def _note(vault):
    return vault / "Papers" / "lecun2015deep.md"


def test_first_write_creates_the_papers_folder_and_the_note(vault):
    outcome = VaultWriter(vault).write(sample_content())

    assert outcome is WriteOutcome.CREATED
    assert _note(vault).read_text(encoding="utf-8") == compose_note(None, sample_content())
    assert [p.name for p in (vault / "Papers").iterdir()] == ["lecun2015deep.md"]  # gecici dosya kalmadi


def test_writing_the_same_content_again_does_not_touch_the_file(vault):
    writer = VaultWriter(vault)
    writer.write(sample_content())
    os.utime(_note(vault), ns=(1_000_000_000, 1_000_000_000))  # eski bir zaman damgasi
    before = _note(vault).stat()

    outcome = writer.write(sample_content())

    after = _note(vault).stat()
    assert outcome is WriteOutcome.UNCHANGED and after.st_mtime_ns == before.st_mtime_ns


def test_update_changes_only_the_generated_block_and_keeps_the_users_edits(vault):
    writer = VaultWriter(vault)
    writer.write(sample_content())
    mine = _note(vault).read_text(encoding="utf-8").replace("# Deep learning\n", "# Deep learning\n\nBenim notum.\n")
    _note(vault).write_text(mine + "\nSon söz.\n", encoding="utf-8")
    changed = NoteContent(DOCUMENT, INFO, "lecun2015deep", [annotation("W3X4", quote="yeni alıntı")])

    outcome = writer.write(changed)

    text = _note(vault).read_text(encoding="utf-8")
    assert outcome is WriteOutcome.UPDATED
    assert "Benim notum." in text and text.rstrip().endswith("Son söz.")  # blogun sonrasindaki kullanici metni yerinde
    assert "yeni alıntı" in text and "Model   doğruluğu" not in text


def test_a_file_changed_by_the_user_between_read_and_replace_is_merged_again_not_overwritten(vault, monkeypatch):
    writer = VaultWriter(vault)
    writer.write(sample_content())
    path = _note(vault)
    calls = {"count": 0}
    original = VaultWriter._replace

    def racing(self, target, text, bom, before):
        calls["count"] += 1
        if calls["count"] == 1:  # Obsidian'da kullanici tam bu sirada kaydediyor
            path.write_text(path.read_text(encoding="utf-8") + "\nAnlik kullanici satiri.\n", encoding="utf-8")
            os.utime(path, ns=(time.time_ns() + 5_000_000_000,) * 2)
        return original(self, target, text, bom, before)

    monkeypatch.setattr(VaultWriter, "_replace", racing)
    changed = NoteContent(DOCUMENT, INFO, "lecun2015deep", [annotation("W3X4", quote="yeni alıntı")])

    assert writer.write(changed) is WriteOutcome.UPDATED

    text = path.read_text(encoding="utf-8")
    assert "Anlik kullanici satiri." in text and "yeni alıntı" in text and calls["count"] == 2


def test_a_file_that_never_stops_changing_raises_a_conflict_and_loses_nothing(vault, monkeypatch):
    writer = VaultWriter(vault)
    writer.write(sample_content())
    path = _note(vault)
    original = VaultWriter._replace

    def always_racing(self, target, text, bom, before):
        path.write_text(path.read_text(encoding="utf-8") + "x", encoding="utf-8")
        return original(self, target, text, bom, before)

    monkeypatch.setattr(VaultWriter, "_replace", always_racing)
    content = NoteContent(DOCUMENT, INFO, "lecun2015deep", [annotation("W3X4", quote="yeni")])

    with pytest.raises(VaultConflictError):
        writer.write(content)

    assert "yeni" not in path.read_text(encoding="utf-8").replace("yeni=", "")  # yazilmadi
    assert not any(p.name.endswith(".pkm-tmp") for p in (vault / "Papers").iterdir())


def test_utf8_bom_is_preserved_and_does_not_break_frontmatter_detection(vault):
    writer = VaultWriter(vault)
    writer.write(sample_content())
    _note(vault).write_bytes(b"\xef\xbb\xbf" + _note(vault).read_bytes())

    changed = NoteContent(DOCUMENT, INFO, "lecun2015deep", [annotation("W3X4", quote="bom sonrasi")])
    writer.write(changed)

    data = _note(vault).read_bytes()
    assert data.startswith(b"\xef\xbb\xbf---\n") and "bom sonrasi" in data.decode("utf-8-sig")
    assert data.count(b"pkm_id:") == 1  # ikinci frontmatter eklenmedi


def test_a_non_utf8_note_is_rejected_and_left_untouched(vault):
    writer = VaultWriter(vault)
    writer.write(sample_content())
    _note(vault).write_bytes("Türkçe".encode("cp1254") + b"\n")
    original = _note(vault).read_bytes()

    with pytest.raises(VaultNoteError):
        writer.write(sample_content())

    assert _note(vault).read_bytes() == original


def test_a_corrupted_note_is_left_untouched(vault):
    writer = VaultWriter(vault)
    writer.write(sample_content())
    broken = _note(vault).read_text(encoding="utf-8").replace("%% pkm:end annotations %%", "")
    _note(vault).write_text(broken, encoding="utf-8")

    with pytest.raises(VaultNoteError):
        writer.write(sample_content())

    assert _note(vault).read_text(encoding="utf-8") == broken


def test_missing_or_file_root_is_unavailable(tmp_path):
    with pytest.raises(VaultUnavailableError):
        VaultWriter(tmp_path / "yok").check()
    a_file = tmp_path / "dosya.txt"
    a_file.write_text("x")
    with pytest.raises(VaultUnavailableError):
        VaultWriter(a_file).write(sample_content())


def test_papers_that_is_a_file_is_reported_not_overwritten(vault):
    (vault / "Papers").write_text("ben bir dosyayim")

    with pytest.raises(VaultUnavailableError):
        VaultWriter(vault).write(sample_content())

    assert (vault / "Papers").read_text() == "ben bir dosyayim"


def test_unsafe_citekeys_never_reach_the_file_system(vault):
    hostile = NoteContent(DOCUMENT, INFO, "../../kacis")

    with pytest.raises(VaultNoteError):
        VaultWriter(vault).write(hostile)

    assert list(vault.rglob("*.md")) == [] and not (vault.parent / "kacis.md").exists()


def test_a_transient_permission_error_on_replace_is_retried(vault, monkeypatch):
    writer = VaultWriter(vault)
    real_replace = os.replace
    attempts = {"n": 0}

    def flaky(src, dst):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise PermissionError("kilitli")
        return real_replace(src, dst)

    monkeypatch.setattr(vault_writer_module.os, "replace", flaky)
    monkeypatch.setattr(vault_writer_module, "_REPLACE_DELAY", 0)

    assert writer.write(sample_content()) is WriteOutcome.CREATED and attempts["n"] == 3
