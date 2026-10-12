"""Vault ozet notlari: kutuphane dizini (`_Index.md`) ve kelime defteri (`_Kelimeler.md`)."""
import os

import pytest

from pdfkit.domain.annotations import Segment, Term
from pdfkit.domain.errors import VaultNoteError
from pdfkit.domain.vault_summary import (
    IndexContent,
    IndexEntry,
    VocabularyContent,
    VocabularySection,
    compose_summary,
    index_entry_for,
    render_summary_block,
    vocabulary_section_for,
)
from pdfkit.infra.vault_writer import VaultWriter, WriteOutcome
from tests.test_pdfkit.vault_samples import DOCUMENT, sample_content


def _term(word, translation="anlam", page=0, term_id=1, context=None):
    return Term(term_id, f"01HZX3K9M2P4Q6R8S0T1V2W{term_id:03d}", 1, word, translation, context, 0, [Segment(page, 1, 5, "")])


@pytest.fixture()
def vault(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    return root


# ---- dizin ----


def test_index_lists_one_line_per_document_sorted_by_citekey_with_counts():
    content = IndexContent([
        IndexEntry("zeta2020", "Zeta", ("A. Yazar",), 2020, "Tamamlandı", highlights=1),
        index_entry_for(sample_content()),
    ])

    block = render_summary_block(content)

    lines = block.split("\n")
    assert lines[0].startswith("%% pkm:begin index") and lines[-1] == "%% pkm:end index %%"
    assert "### Kaynaklar (2)" in lines
    first, second = (line for line in lines if line.startswith("- [["))
    assert first == "- [[lecun2015deep]] — Deep learning · Yann LeCun, Y. Bengio · 2015 · 3 alıntı, 1 not, 1 kelime · Devam Ediyor"
    assert second == "- [[zeta2020]] — Zeta · A. Yazar · 2020 · 1 alıntı · Tamamlandı"


def test_index_shortens_long_author_lists_and_marks_documents_without_content():
    entry = IndexEntry("x2020a", "Başlık", ("A", "B", "C", "D"), None)

    line = render_summary_block(IndexContent([entry])).split("\n")[4]

    assert line == "- [[x2020a]] — Başlık · A, B, C vd. · henüz not yok"


def test_index_titles_cannot_break_out_of_the_block_or_the_line():
    entry = IndexEntry("x2020a", "Satır\nbir %% iki", (), None)

    lines = render_summary_block(IndexContent([entry])).split("\n")

    assert "- [[x2020a]] — Satır bir % % iki · henüz not yok" in lines  # tek satır, yorum işaretçisi etkisiz
    assert [line for line in lines if "%%" in line] == [lines[0], lines[-1]]  # yalnız iki sentinel satırı


def test_empty_index_says_so():
    assert "_Henüz kaynak yok._" in render_summary_block(IndexContent())


# ---- kelime defteri ----


def test_vocabulary_groups_terms_by_document_alphabetically_with_deep_links():
    section = vocabulary_section_for(sample_content())
    later = VocabularySection(DOCUMENT, "zeta2020", "Zeta", (_term("zebra", "zebra", term_id=5), _term("Apple", "elma", term_id=6)))

    block = render_summary_block(VocabularyContent([later, section]))

    lines = block.split("\n")
    headings = [line for line in lines if line.startswith("### ")]
    assert headings == ["### [[lecun2015deep]] — Deep learning (1)", "### [[zeta2020]] — Zeta (2)"]
    words = [line.split("**")[1] for line in lines if line.startswith("- **")]
    assert words == ["ubiquitous", "Apple", "zebra"]  # belge sirasi, belge icinde alfabetik (buyuk/kucuk harf duyarsiz)
    assert "[s. 5](pkm://open?doc=" in next(line for line in lines if "ubiquitous" in line)


def test_vocabulary_skips_documents_without_terms_and_reports_an_empty_book():
    empty = VocabularySection(DOCUMENT, "bos2020", "Boş", ())

    assert "_Henüz kelime yok._" in render_summary_block(VocabularyContent([empty]))
    assert VocabularyContent([empty]).is_empty and not VocabularyContent([vocabulary_section_for(sample_content())]).is_empty


# ---- birlestirme ----


def test_new_summary_note_gets_a_kind_and_a_title():
    text = compose_summary(None, IndexContent([index_entry_for(sample_content())]))

    assert text.startswith('---\npkm_kind: "index"\n---\n\n# Kütüphane Dizini\n\n%% pkm:begin index')
    assert text.endswith("%% pkm:end index %%\n")


def test_merging_keeps_user_text_around_the_block_and_is_idempotent():
    content = IndexContent([index_entry_for(sample_content())])
    first = compose_summary(None, content)
    edited = first.replace("# Kütüphane Dizini\n", "# Kütüphane Dizini\n\nBenim giriş notum.\n") + "\nAltına yazdım.\n"
    updated = IndexContent([index_entry_for(sample_content()), IndexEntry("yeni2021", "Yeni", (), 2021)])

    merged = compose_summary(edited, updated)

    assert "Benim giriş notum." in merged and merged.endswith("Altına yazdım.\n") and "[[yeni2021]]" in merged
    assert merged.count("%% pkm:begin index") == 1
    assert compose_summary(merged, updated) == merged


def test_merging_preserves_crlf_line_endings():
    content = IndexContent([index_entry_for(sample_content())])
    crlf = compose_summary(None, content).replace("\n", "\r\n")

    merged = compose_summary(crlf, IndexContent())

    assert "\r\n" in merged and "\n" not in merged.replace("\r\n", "")


def test_a_note_without_the_block_gets_it_appended():
    merged = compose_summary("# Benim dizinim\n\nkendi yazım\n", IndexContent())

    assert merged.startswith("# Benim dizinim\n\nkendi yazım\n\n%% pkm:begin index") and merged.endswith("%% pkm:end index %%\n")


@pytest.mark.parametrize(
    "broken",
    [
        "# Not\n%% pkm:end index %%\n",
        "# Not\n%% pkm:begin index — x %%\nA\n",
        "# Not\n%% pkm:end index %%\n%% pkm:begin index — x %%\n",
    ],
)
def test_corrupted_sentinels_are_rejected(broken):
    with pytest.raises(VaultNoteError):
        compose_summary(broken, IndexContent())


def test_the_two_summary_kinds_do_not_interfere():
    vocabulary = compose_summary(None, VocabularyContent([vocabulary_section_for(sample_content())]))

    merged = compose_summary(vocabulary, IndexContent())  # dizin blogu olmayan dosyaya eklenir, kelime blogu bozulmaz

    assert "%% pkm:begin vocabulary" in merged and "%% pkm:begin index" in merged


# ---- yazici ----


def test_writer_creates_updates_and_skips_unchanged_summaries(vault):
    writer = VaultWriter(vault)
    content = IndexContent([index_entry_for(sample_content())])
    target = vault / "Papers" / "_Index.md"

    assert writer.write_summary(content) is WriteOutcome.CREATED
    os.utime(target, ns=(1_000_000_000, 1_000_000_000))
    before = target.stat().st_mtime_ns
    assert writer.write_summary(content) is WriteOutcome.UNCHANGED
    assert target.stat().st_mtime_ns == before
    assert writer.write_summary(IndexContent()) is WriteOutcome.UPDATED
    assert [p.name for p in (vault / "Papers").iterdir()] == ["_Index.md"]


def test_an_empty_summary_is_not_created_but_is_updated_when_the_file_exists(vault):
    writer = VaultWriter(vault)
    target = vault / "Papers" / "_Kelimeler.md"

    assert writer.write_summary(VocabularyContent()) is WriteOutcome.UNCHANGED
    assert not target.exists()
    writer.write_summary(VocabularyContent([vocabulary_section_for(sample_content())]))
    assert target.exists()
    assert writer.write_summary(VocabularyContent()) is WriteOutcome.UPDATED
    assert "_Henüz kelime yok._" in target.read_text(encoding="utf-8")


def test_a_corrupted_summary_file_is_left_untouched(vault):
    (vault / "Papers").mkdir()
    target = vault / "Papers" / "_Index.md"
    target.write_text("# Dizin\n%% pkm:end index %%\n", encoding="utf-8")

    with pytest.raises(VaultNoteError):
        VaultWriter(vault).write_summary(IndexContent())

    assert target.read_text(encoding="utf-8") == "# Dizin\n%% pkm:end index %%\n"
