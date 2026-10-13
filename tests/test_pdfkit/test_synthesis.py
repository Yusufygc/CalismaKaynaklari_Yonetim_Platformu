"""Literatur matrisi: gruplama, suzgecler, Markdown tablosu (kacirma, kisaltma, baglanti), vault matris notu."""
from pathlib import Path

import pytest

from pdfkit.domain.annotations import STATUS_ORPHANED
from pdfkit.domain.errors import VaultNoteError
from pdfkit.domain.models import Document, SourceInfo
from pdfkit.domain.synthesis import (
    MAX_QUOTE_LENGTH,
    MatrixFilter,
    build_row,
    column_keys,
    make_matrix,
    render_markdown,
    render_table,
)
from pdfkit.domain.vault_summary import MatrixContent, compose_summary, matrix_row_for
from pdfkit.infra.vault_writer import VaultWriter, WriteOutcome
from tests.test_pdfkit.vault_samples import DOCUMENT, INFO, annotation, sample_content

GOLDEN = Path(__file__).parent / "golden" / "matrix.golden"
OTHER_DOCUMENT = Document(2, "cd" * 32, "store/cd/y.pdf", 10, 8, True, None, None, None, "local", None, None)
OTHER_INFO = SourceInfo("Attention is all you need", ("A. Vaswani",), 2017, None, "Tamamlandı")


def sample_rows():
    first = build_row(
        DOCUMENT, INFO, "lecun2015deep",
        [
            annotation("W3X4", "method", "Evrişimli ağlar kullanıldı.", "Yöntem bölümü", ["hipotez"], page=2, start=10, annotation_id=1),
            annotation("WA11", "method", "Geri yayılım ile eğitildi.", None, ["hipotez", "ortak"], page=1, start=4, annotation_id=2),
            annotation("WB22", "finding", "Doğruluk %92 oldu.", None, [], page=4, annotation_id=3),
            annotation("WC33", "critique", "Kayıp metin", None, [], page=0, status=STATUS_ORPHANED, annotation_id=4),
        ],
        resource_id=7,
    )
    second = build_row(
        OTHER_DOCUMENT, OTHER_INFO, "vaswani2017attention",
        [
            annotation("WD44", "method", "Yalnızca dikkat katmanları.", None, ["ortak"], page=0, annotation_id=5),
            annotation("WE55", "general", "Genel not", None, [], page=3, annotation_id=6),
        ],
        resource_id=9,
    )
    return [second, first]  # sirasiz verilir: matris citekey'e gore siralar


def test_columns_are_the_five_labels_in_definition_order_plus_general():
    assert column_keys() == ("important", "finding", "method", "concept", "critique", "general")


def test_a_row_groups_annotations_by_label_in_page_order_and_keeps_unknown_labels_in_general():
    row = sample_rows()[1]

    assert [a.page for a in row.cells["method"]] == [1, 2]  # sayfa sirasiyla (verilis sirasi degil)
    assert set(row.cells) == {"method", "finding", "critique"} and row.annotation_count == 4
    odd = build_row(DOCUMENT, INFO, None, [annotation("WZZ9", "uydurma", "x")])
    assert set(odd.cells) == {"general"}


def test_rows_are_sorted_by_citekey_and_documents_without_a_citekey_go_last():
    nokey = build_row(OTHER_DOCUMENT, SourceInfo("Anahtarsız"), None, [annotation("WF66", "method", "x")])

    matrix = make_matrix([nokey] + sample_rows())

    assert [r.citekey for r in matrix.rows] == ["lecun2015deep", "vaswani2017attention", None]


def test_label_filter_restricts_columns_and_drops_rows_left_without_annotations():
    matrix = make_matrix(sample_rows(), MatrixFilter(labels=("finding",)))

    assert matrix.columns == ("finding",)
    assert [r.citekey for r in matrix.rows] == ["lecun2015deep"]  # ikinci makalede Bulgu alintisi yok


def test_tag_filter_keeps_only_tagged_annotations_and_is_normalized():
    matrix = make_matrix(sample_rows(), MatrixFilter(tag="#Ortak"))

    cells = {r.citekey: {k: [a.uid[-4:] for a in v] for k, v in r.cells.items()} for r in matrix.rows}
    assert cells == {"lecun2015deep": {"method": ["WA11"]}, "vaswani2017attention": {"method": ["WD44"]}}


def test_document_filter_limits_rows_and_an_unmatched_filter_gives_an_empty_matrix():
    only = make_matrix(sample_rows(), MatrixFilter(document_ids=frozenset({2})))

    assert [r.citekey for r in only.rows] == ["vaswani2017attention"]
    empty = make_matrix(sample_rows(), MatrixFilter(tag="yok"))
    assert empty.rows == () and render_table(empty) == []
    assert "_Eşleşen alıntı yok._" in render_markdown(empty)


def test_markdown_table_matches_the_golden_file():
    assert render_markdown(make_matrix(sample_rows())) == GOLDEN.read_text(encoding="utf-8")


def test_table_keeps_one_row_per_line_and_cells_cannot_break_it():
    nasty = build_row(
        DOCUMENT, SourceInfo("Başlık | ile\nsatır sonu", year=2020), "x2020a",
        [annotation("WG77", "method", "a | b <script>x</script> %% c\\|d\nsatır", "yorum | boru", [], page=0)],
    )

    lines = render_table(make_matrix([nasty]))

    assert len(lines) == 3  # baslik, ayirici, tek satir
    row = lines[2]
    cells = [c for c in row.replace("\\|", "\x00").split("|")]  # kacirilmis boru hucre ayirici degil
    assert len(cells) == 1 + 7 + 1  # bas/son bosluk + Kaynak + 6 sutun
    assert "<script>" not in row and "&lt;script&gt;" in row and "a \\| b" in row
    assert "% %" in row and "%%" not in row
    assert "c\\\\\\|d" in row  # ters bolu ve boru birlikte: kacis bozulmaz


def test_long_quotes_are_shortened_with_an_ellipsis():
    long = build_row(DOCUMENT, INFO, "u2020a", [annotation("WH88", "method", "kelime " * 100, None, [], page=0)])

    row = render_table(make_matrix([long]))[2]

    assert "…”" in row and row.count("kelime") < 100 and len(row) < MAX_QUOTE_LENGTH + 400


def test_orphans_are_listed_without_a_link_and_located_ones_link_to_the_pdf():
    row = render_table(make_matrix(sample_rows()))[2]  # lecun satiri (citekey sirasiyla ilk)

    assert "• “Kayıp metin”" in row and "Kayıp metin” (" not in row  # yetim: baglanti yok
    assert "[s. 3](pkm://open?doc=" in row and "&ann=" in row


# ---- vault matris notu ----


def test_matrix_content_note_is_created_idempotent_and_keeps_user_text():
    content = MatrixContent(sample_rows())

    first = compose_summary(None, content)
    assert first.startswith('---\npkm_kind: "matrix"\n---\n\n# Literatür Matrisi\n\n%% pkm:begin matrix')
    assert "_2 kaynak · 6 alıntı_" in first and "| [[lecun2015deep]] · Deep learning (2015) |" in first
    edited = first.replace("# Literatür Matrisi\n", "# Literatür Matrisi\n\nBenim notlarım.\n") + "\nAltına yazdım.\n"
    assert compose_summary(edited, content) == edited


def test_an_empty_matrix_says_so_and_the_writer_does_not_create_the_file(tmp_path):
    assert "_Henüz alıntı yok._" in compose_summary(None, MatrixContent())
    vault = tmp_path / "vault"
    vault.mkdir()

    assert VaultWriter(vault).write_summary(MatrixContent()) is WriteOutcome.UNCHANGED
    assert not (vault / "Papers" / "_Matris.md").exists()
    assert VaultWriter(vault).write_summary(MatrixContent(sample_rows())) is WriteOutcome.CREATED
    assert VaultWriter(vault).write_summary(MatrixContent(sample_rows())) is WriteOutcome.UNCHANGED


def test_a_corrupted_matrix_note_is_rejected_untouched():
    with pytest.raises(VaultNoteError):
        compose_summary("# Matris\n%% pkm:end matrix %%\n", MatrixContent(sample_rows()))


def test_a_note_content_converts_to_a_matrix_row():
    row = matrix_row_for(sample_content())

    assert row.citekey == "lecun2015deep" and row.title == "Deep learning" and row.annotation_count == 3
