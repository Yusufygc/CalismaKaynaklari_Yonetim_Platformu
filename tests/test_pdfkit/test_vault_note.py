"""Vault notu (saf cekirdek): altin dosya, idempotentlik, kullanici metninin korunmasi, bozuk girdilerin reddi."""
from pathlib import Path

import pytest

from pdfkit.domain.errors import VaultNoteError
from pdfkit.domain.vault_note import (
    BEGIN_MARKER,
    SENTINEL_BEGIN,
    SENTINEL_END,
    NoteContent,
    block_id,
    compose_note,
    managed_fields,
    note_rel_path,
    obsidian_tag,
    render_block,
)
from tests.test_pdfkit.vault_samples import DOCUMENT, INFO, annotation, sample_content

GOLDEN = Path(__file__).parent / "golden" / "vault_note.golden"


def _empty(info=INFO):
    return NoteContent(DOCUMENT, info, "lecun2015deep")


def test_new_note_matches_the_golden_file():
    assert compose_note(None, sample_content()) == GOLDEN.read_text(encoding="utf-8")


def test_composing_twice_changes_nothing():
    first = compose_note(None, sample_content())

    assert compose_note(first, sample_content()) == first
    assert compose_note("", sample_content()) == first  # bos dosya yeni not gibi davranir


def test_block_is_ordered_by_page_with_orphans_last_and_each_item_has_a_stable_block_id():
    block = render_block(sample_content())

    pages = [line for line in block.splitlines() if line.startswith("> [!")]
    assert [line.split("]")[0] for line in pages] == ["> [!note", "> [!finding", "> [!critique", "> [!note"]  # genel, bulgu, yetim, sayfa notu
    assert block.index("Genel") < block.index("Bulgu") < block.index("konumu bulunamadı")  # sayfa sirasi, yetim sonda
    assert block.count("^hl-") == 3 and "^hl-t1v2w3x4" in block and "^nt-t1v2wnnn" in block
    assert block_id("hl", "01HZX3K9M2P4Q6R8S0T1V2W3X4") == "hl-t1v2w3x4"


def test_every_callout_page_number_is_a_deep_link_with_one_based_page_and_the_annotation_uid():
    block = render_block(sample_content())

    assert "[s. 3](pkm://open?doc=abababababababab&page=3&ann=01HZX3K9M2P4Q6R8S0T1V2W3X4)" in block
    assert "konumu bulunamadı" in block and "pkm://open?doc=abababababababab&page=2" not in block  # yetimin baglantisi yok


def test_user_text_cannot_break_the_sentinels_or_inject_markup():
    hostile = annotation("W3X4", quote="a %% pkm:end annotations %% b", comment="%% pkm:begin annotations", tags=["x y", "#a/b", "ç-ö"])
    block = render_block(NoteContent(DOCUMENT, INFO, "lecun2015deep", [hostile]))

    assert block.count("%%") == 4  # yalniz iki sentinel satiri (her biri iki isaretci)
    assert "% % pkm:end annotations % %" in block
    assert "#x-y #a/b #ç-ö" in block


def test_empty_content_still_produces_a_valid_block():
    block = render_block(_empty())

    assert block.startswith(SENTINEL_BEGIN) and block.endswith(SENTINEL_END) and "Henüz alıntı" in block


def test_obsidian_tag_rules():
    assert obsidian_tag("#Hipotez ") == "Hipotez"
    assert obsidian_tag("iki kelime") == "iki-kelime"
    assert obsidian_tag("a!b?c") == "abc"
    assert obsidian_tag("2024") == "" and obsidian_tag("###") == "" and obsidian_tag("") == ""


def test_managed_frontmatter_omits_empty_values_and_quotes_strings():
    info = INFO.__class__("Başlık: \"alıntılı\"", (), None, None, "")

    fields = managed_fields(NoteContent(DOCUMENT, info, "anon", ()))

    assert set(fields) == {"pkm_id", "citekey", "title"}
    assert fields["title"] == '"Başlık: \\"alıntılı\\""' and fields["pkm_id"] == "abababababababab"


# ---- Birlestirme: kullanici metni korunur ----


def test_text_before_and_after_the_block_and_unmanaged_frontmatter_survive_updates():
    created = compose_note(None, sample_content())
    edited = created.replace("tags: [paper]", "tags: [paper, benim-etiketim]\naliases:\n  - dl\n  - derin").replace(
        "# Deep learning\n", "# Deep learning\n\nBenim giriş notum.\n"
    ) + "\n## Benim yorumlarım\nBurası kullanıcıya ait.\n"

    new_content = NoteContent(DOCUMENT, INFO.__class__("Deep learning", INFO.authors, 2015, INFO.doi, "Tamamlandı"), "lecun2015deep",
                              [annotation("W3X4", quote="yeni alıntı")])
    updated = compose_note(edited, new_content)

    assert "tags: [paper, benim-etiketim]\naliases:\n  - dl\n  - derin" in updated  # yonetilmeyen satirlar aynen
    assert "Benim giriş notum." in updated and updated.endswith("## Benim yorumlarım\nBurası kullanıcıya ait.\n")
    assert 'status: "Tamamlandı"' in updated and "Devam Ediyor" not in updated  # yonetilen anahtar guncellendi
    assert "yeni alıntı" in updated and "Model   doğruluğu" not in updated and updated.count(BEGIN_MARKER) == 1
    assert compose_note(updated, new_content) == updated  # ve hala idempotent


def test_existing_note_without_sentinels_gets_the_block_appended_and_frontmatter_added():
    mine = "# Benim notum\n\nSerbest metin.\n"

    merged = compose_note(mine, sample_content())

    assert merged.startswith("---\npkm_id: abababababababab\n")
    assert "# Benim notum\n\nSerbest metin.\n\n" + SENTINEL_BEGIN in merged
    assert merged.endswith(SENTINEL_END + "\n") and compose_note(merged, sample_content()) == merged


def test_crlf_files_stay_crlf_and_are_idempotent():
    created = compose_note(None, sample_content()).replace("\n", "\r\n")

    updated = compose_note(created, NoteContent(DOCUMENT, INFO, "lecun2015deep", [annotation("W3X4", quote="yeni")]))

    assert "\r\n" in updated and "\n" not in updated.replace("\r\n", "")
    assert compose_note(updated, NoteContent(DOCUMENT, INFO, "lecun2015deep", [annotation("W3X4", quote="yeni")])) == updated


def test_new_frontmatter_key_is_added_to_a_note_that_lacks_it_without_touching_other_keys():
    old = "---\ntitle: \"Eski\"\nmy_key: 5\n---\n\n# Eski\n\n" + SENTINEL_BEGIN + "\n\nx\n\n" + SENTINEL_END + "\n"

    updated = compose_note(old, sample_content())

    assert "my_key: 5" in updated and 'title: "Deep learning"' in updated and "doi:" in updated and "pkm_id:" in updated


@pytest.mark.parametrize(
    "broken",
    [
        "# Not\n" + SENTINEL_BEGIN + "\nyarim\n",  # bitis yok
        "# Not\n" + SENTINEL_END + "\n",  # baslangic yok
        "# Not\n" + SENTINEL_END + "\n" + SENTINEL_BEGIN + "\n",  # ters sira
        "# Not\n" + SENTINEL_BEGIN + "\na\n" + SENTINEL_END + "\n" + SENTINEL_BEGIN + "\nb\n" + SENTINEL_END + "\n",  # iki blok
        "---\ntitle: x\n# Not\n",  # frontmatter kapanmamis
    ],
    ids=["no-end", "no-begin", "reversed", "duplicate", "open-frontmatter"],
)
def test_corrupted_notes_are_rejected_instead_of_overwritten(broken):
    with pytest.raises(VaultNoteError):
        compose_note(broken, sample_content())


def test_note_path_is_derived_only_from_a_safe_citekey():
    assert note_rel_path("lecun2015deep") == "Papers/lecun2015deep.md"
    for bad in ("../x", "a/b", "A", "", "x" * 81, "a b", "a.md"):
        with pytest.raises(VaultNoteError):
            note_rel_path(bad)
